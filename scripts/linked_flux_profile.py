"""Fixed-position, shared-amplitude linear profile with per-frame nuisance.

For frame i, data = amplitude * coefficient_i * template_i + nuisance_i @ b_i.
Response coefficients and nuisance columns are dimensionless. The amplitude
unit times the template unit must equal the data unit exactly. All data/error
units must agree across frames; nuisance coefficients use the data unit.
Whitening assumes supplied within-frame covariance blocks are mutually
independent. Results are conditional on the supplied templates, responses,
positions, masks and known covariance; this is not a calibrated sky fit.
"""
from dataclasses import dataclass
from numbers import Real

import numpy as np
from astropy import units as u


@dataclass(frozen=True)
class LinkedFluxResult:
    amplitude: float
    amplitude_error: float
    amplitude_variance: float
    data_unit: str
    amplitude_unit: str
    nuisance: tuple
    residuals: tuple
    whitened_residuals: tuple
    coefficient_provenance: tuple
    nuisance_ranks: tuple
    rank: int
    parameters: int
    dof: int
    chi2: float
    profile_information: float
    scaled_condition: float


def _array(value, name, ndim):
    a=np.asarray(value)
    if a.ndim!=ndim or a.dtype.kind not in 'iuf':
        raise ValueError(name+' must be a real numeric array of the required dimension')
    a=np.asarray(a,dtype=float)
    if not np.isfinite(a).all():raise ValueError(name+' must be finite')
    return a


def _unit(value, name):
    if not isinstance(value,str) or not value.strip():raise ValueError(name+' must be an explicit unit string')
    try:return u.Unit(value)
    except (ValueError,TypeError) as exc:raise ValueError('invalid '+name) from exc


def _scaled_svd(matrix, rcond, label):
    n,p=matrix.shape
    if p==0:return np.empty((n,0)),np.empty(0),np.empty((0,0)),np.empty(0)
    norms=np.linalg.norm(matrix,axis=0)
    if not np.isfinite(norms).all() or np.any(norms<=0):raise ValueError(label+' has a zero or invalid column')
    try:U,s,Vh=np.linalg.svd(matrix/norms,full_matrices=False)
    except np.linalg.LinAlgError as exc:raise ValueError(label+' SVD failed') from exc
    if len(s)!=p or not np.isfinite(s).all() or s[-1]<=rcond*s[0]:
        raise ValueError(label+' rank deficient or poorly conditioned')
    return U,s,Vh,norms


def _unpack(frame, common_unit, common_amplitude_unit):
    if not isinstance(frame,dict):raise ValueError('each frame must be a dict')
    required={'data','template','nuisance','coefficient','coefficient_provenance',
              'data_unit','amplitude_unit','template_unit','nuisance_unit','coefficient_unit'}
    allowed=required|{'error','error_unit','covariance','covariance_unit'}
    if not required.issubset(frame) or set(frame)-allowed:raise ValueError('missing or unknown frame fields')
    mode_error='error' in frame or 'error_unit' in frame
    mode_cov='covariance' in frame or 'covariance_unit' in frame
    if mode_error==mode_cov or (mode_error and not {'error','error_unit'}.issubset(frame)) or (mode_cov and not {'covariance','covariance_unit'}.issubset(frame)):
        raise ValueError('provide exactly one error/unit or covariance/unit pair')
    data_unit=_unit(frame['data_unit'],'data unit')
    if data_unit==u.dimensionless_unscaled or (common_unit is not None and data_unit!=common_unit):
        raise ValueError('all data must use the same explicit physical unit')
    amplitude_unit=_unit(frame['amplitude_unit'],'amplitude unit')
    template_unit=_unit(frame['template_unit'],'template unit')
    if amplitude_unit==u.dimensionless_unscaled or (common_amplitude_unit is not None and amplitude_unit!=common_amplitude_unit) or amplitude_unit*template_unit!=data_unit:
        raise ValueError('amplitude times template units must exactly match data unit')
    for key in ('nuisance_unit','coefficient_unit'):
        if _unit(frame[key],key)!=u.dimensionless_unscaled:raise ValueError(key+' must be dimensionless')
    prov=frame['coefficient_provenance']
    if not isinstance(prov,str) or not prov.strip():raise ValueError('coefficient provenance must be supplied')
    coef=frame['coefficient']
    if isinstance(coef,(bool,np.bool_)) or not isinstance(coef,Real) or not np.isfinite(coef):raise ValueError('coefficient must be finite and real')
    y=_array(frame['data'],'data',1);t=_array(frame['template'],'template',1);N=_array(frame['nuisance'],'nuisance',2)
    if not len(y) or t.shape!=y.shape or N.shape[0]!=len(y):raise ValueError('frame shape mismatch')
    g=float(coef)*t
    if not np.isfinite(g).all():raise ValueError('scaled template invalid')
    if mode_error:
        if _unit(frame['error_unit'],'error unit')!=data_unit:raise ValueError('error unit mismatch')
        e=_array(frame['error'],'error',1)
        if e.shape!=y.shape or np.any(e<=0):raise ValueError('error must be positive and match data')
        wy=y/e; wg=g/e; wN=N/e[:,None]
    else:
        if _unit(frame['covariance_unit'],'covariance unit')!=data_unit**2:raise ValueError('covariance unit mismatch')
        C=_array(frame['covariance'],'covariance',2)
        if C.shape!=(len(y),len(y)):raise ValueError('covariance shape mismatch')
        scale=np.max(np.abs(C))
        if scale==0 or np.max(np.abs(C-C.T))>64*np.finfo(float).eps*len(y)*scale:
            raise ValueError('covariance must be symmetric at its own scale')
        C=(C+C.T)/2
        try:L=np.linalg.cholesky(C)
        except np.linalg.LinAlgError as exc:raise ValueError('covariance must be positive definite') from exc
        wy=np.linalg.solve(L,y);wg=np.linalg.solve(L,g);wN=np.linalg.solve(L,N)
    if not all(np.isfinite(v).all() for v in (wy,wg,wN)):raise ValueError('whitened arrays invalid')
    return data_unit,amplitude_unit,y,g,N,wy,wg,wN,prov


def profile_shared_amplitude(frames, *, rcond=1e-10):
    """Profile independent nuisance parameters with SVD; signed amplitude allowed.

    Each frame supplies data/template vectors and an n-by-k nuisance matrix,
    a fixed numerical coefficient with nonempty provenance, explicit data,
    amplitude, template, nuisance and coefficient units, and either positive error vector
    plus its unit or full positive definite covariance plus its squared unit.
    Negative amplitude is intentionally not clipped or constrained.
    """
    if not isinstance(frames,(list,tuple)) or not frames:raise ValueError('nonempty frame sequence required')
    if isinstance(rcond,(bool,np.bool_)) or not isinstance(rcond,Real) or not np.isfinite(rcond) or not 0<rcond<1:raise ValueError('invalid rcond')
    unpacked=[];unit=None;amp_unit=None
    for frame in frames:
        values=_unpack(frame,unit,amp_unit);unit=values[0];amp_unit=values[1];unpacked.append(values)
    total=sum(len(x[2]) for x in unpacked); p=1+sum(x[4].shape[1] for x in unpacked)
    if total<=p:raise ValueError('model must have positive residual degrees of freedom')
    X=np.zeros((total,p));Y=np.empty(total);row=0;col=1
    prof_num=0.;info=0.; bases=[];ranks=[]
    for _,_,y,g,N,wy,wg,wN,_ in unpacked:
        n=len(y);k=N.shape[1]
        U,s,Vh,norms=_scaled_svd(wN,rcond,'per-frame nuisance')
        projected_g=wg-U@(U.T@wg); projected_y=wy-U@(U.T@wy)
        prof_num+=float(projected_g@projected_y);info+=float(projected_g@projected_g)
        X[row:row+n,0]=wg;X[row:row+n,col:col+k]=wN;Y[row:row+n]=wy
        bases.append((U,s,Vh,norms));ranks.append(k);row+=n;col+=k
    _,s,Vh,norms=_scaled_svd(X,rcond,'joint design')
    if not np.isfinite(info) or info<=0 or not np.isfinite(prof_num):raise ValueError('profile information invalid')
    amplitude=prof_num/info;variance=1.0/info
    # Independent SVD expression for the source covariance; guards numerical
    # inconsistencies without replacing a singular design by a pseudoinverse.
    svd_variance=float(np.sum((Vh[:,0]/s/norms[0])**2))
    if not np.isfinite(amplitude) or not np.isfinite(variance) or variance<=0 or not np.isclose(variance,svd_variance,rtol=1e-6,atol=0):
        raise ValueError('unstable profile covariance')
    nuisance=[];residuals=[];whitened=[]
    for (_,_,y,g,N,wy,wg,wN,_),(U,sn,Vhn,nn) in zip(unpacked,bases):
        b=(Vhn.T@((U.T@(wy-amplitude*wg))/sn))/nn if len(sn) else np.empty(0)
        residual=y-amplitude*g-N@b;wr=wy-amplitude*wg-wN@b
        if not np.isfinite(b).all() or not np.isfinite(residual).all() or not np.isfinite(wr).all():raise ValueError('nonfinite solution')
        nuisance.append(b);residuals.append(residual);whitened.append(wr)
    chi2=sum(float(r@r) for r in whitened)
    if not np.isfinite(chi2):raise ValueError('nonfinite residual statistic')
    return LinkedFluxResult(float(amplitude),float(np.sqrt(variance)),float(variance),str(unit),str(amp_unit),
        tuple(nuisance),tuple(residuals),tuple(whitened),tuple(x[8] for x in unpacked),
        tuple(ranks),p,p,total-p,chi2,float(info),float(s[0]/s[-1]))
