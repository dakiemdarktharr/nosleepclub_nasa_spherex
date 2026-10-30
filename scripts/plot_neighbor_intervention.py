"""Offline all-completed vector and paired-error plots; no fitting/selection."""
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ft2font import FT2Font
import numpy as np


ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'web/data/neighbor-intervention'
OVERVIEW=FOLDER/'overview.json'
CONTROLS=FOLDER/'controls.json'
VARIANTS=('plane_nearest_free','plane_nearest_nonnegative','plane_bilinear_free','plane_bilinear_nonnegative',
          'quadratic_nearest_free','quadratic_nearest_nonnegative','quadratic_bilinear_free','quadratic_bilinear_nonnegative')
COLORS=('#8fd8ec','#b7b2ff','#ffa85c','#facb69')
CASES=('plane_300uJy','plane_600uJy','quadratic_300uJy','quadratic_600uJy')


def digest(path):return sha256(path.read_bytes()).hexdigest()


def save(fig,path):
    fig.savefig(path,format='svg',metadata={'Date':None,'Creator':'Matplotlib; scripts.plot_neighbor_intervention'})
    lines=path.read_bytes().replace(b'\r\n',b'\n').split(b'\n')
    path.write_bytes(b'\n'.join(line.rstrip(b' \t') for line in lines));plt.close(fig)
    return {'path':path.relative_to(ROOT/'web').as_posix(),'sha256':digest(path),'bytes':path.stat().st_size}


def label(index):
    background='Plane' if index<4 else 'Bậc hai';spatial='gần' if index%4<2 else 'nội suy'
    sign='có dấu' if index%2==0 else 'không âm'
    return f'{index+1} · {background} / {spatial} / {sign}'


def render():
    overview=json.loads(OVERVIEW.read_text(encoding='utf-8'));controls=json.loads(CONTROLS.read_text(encoding='utf-8'))
    if overview['schema']!='neighbor-intervention-overview-1' or overview['counts']['recorded']!=288:
        raise ValueError('completed audited overview required')
    font_path=font_manager.findfont('DejaVu Sans',fallback_to_default=False)
    texts=[label(i) for i in range(8)]+['Đổi về đông so nhánh 1 (″)','Đổi về bắc (″)',
        'Bộ rộng · ảnh thật','Bộ chặt · ảnh thật','Đối chứng tổng hợp · cùng realization',
        'Sai lệch khi hàng xóm có dấu (″)','Sai lệch khi hàng xóm không âm (″)',
        '×: chưa qua sàng lọc số; không vẽ ellipse sai số.',
        'Mũi tên nối hai ràng buộc trên cùng nền/ePSF.',
        'Nền plane · 300 µJy','Nền plane · 600 µJy','Nền bậc hai · 300 µJy','Nền bậc hai · 600 µJy',
        'Mọi cặp fit được, kể cả chưa qua sàng lọc số. Một geometry; noise oracle có điều kiện.']
    glyphs=FT2Font(font_path).get_charmap()
    missing={c for text in texts for c in text if not c.isspace() and ord(c) not in glyphs}
    if missing:raise ValueError('font lacks plotted glyphs: '+repr(sorted(missing)))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#111923',
        'axes.facecolor':'#111923','axes.edgecolor':'#8b9aaa','text.color':'#eef3fa',
        'axes.labelcolor':'#eef3fa','xtick.color':'#dce5ef','ytick.color':'#dce5ef',
        'grid.color':'#455466','svg.hashsalt':'neighbor-intervention-v1','svg.fonttype':'path'})
    result={'version':'0.10.0-neighbor-figures.1','source_overview_sha256':digest(OVERVIEW),
        'source_controls_sha256':digest(CONTROLS),'script_sha256':digest(Path(__file__)),
        'dependency_manifest_sha256':digest(ROOT/'requirements-figures.txt'),
        'packages':{n:version(n) for n in ('matplotlib','numpy','Pillow','fonttools')},
        'font':{'family':'DejaVu Sans','sha256':digest(Path(font_path))},'figures':[],
        'qualification':'opened-data model sensitivity and one-geometry synthetic oracle-noise controls, not real-source accuracy or calibrated confidence'}
    for group in overview['real']['configurations']:
        rows={r['variant']:r for r in group['pairs']};base=rows[VARIANTS[0]]['east_north_arcsec']
        delta={v:np.asarray(row['east_north_arcsec'])-base for v,row in rows.items() if base is not None and row['east_north_arcsec'] is not None}
        fig,ax=plt.subplots(figsize=(9.5,5.8));fig.subplots_adjust(left=.13,bottom=.21,right=.60,top=.79)
        for i,variant in enumerate(VARIANTS):
            if variant not in delta:continue
            x,y=delta[variant];color=COLORS[i//2];marker='o' if i<4 else 's'
            ax.scatter(x,y,s=70,marker=marker,facecolor=color if i%2 else 'none',edgecolor=color,
                       linewidth=1.5,label=label(i),zorder=3)
            if not rows[variant]['numerical_support_both']:ax.scatter(x,y,s=42,marker='x',color='#fff',linewidths=1.0,zorder=4)
            angle=2*np.pi*i/8
            ax.annotate(str(i+1),(x,y),textcoords='offset points',xytext=(13*np.cos(angle),13*np.sin(angle)),fontsize=10)
        for i in (0,2,4,6):
            if VARIANTS[i] in delta and VARIANTS[i+1] in delta:
                ax.annotate('',xy=delta[VARIANTS[i+1]],xytext=delta[VARIANTS[i]],
                            arrowprops={'arrowstyle':'->','lw':1.1,'color':COLORS[i//2],'alpha':.8})
        values=np.array(list(delta.values())) if delta else np.zeros((1,2))
        low=np.minimum(values.min(axis=0),0);high=np.maximum(values.max(axis=0),0)
        center=(low+high)/2;span=max(.1,float(np.max(high-low))*1.45)
        ax.set_xlim(center[0]-span/2,center[0]+span/2);ax.set_ylim(center[1]-span/2,center[1]+span/2)
        ax.set_aspect('equal',adjustable='box');ax.axhline(0,color='#8b9aaa',lw=.8);ax.axvline(0,color='#8b9aaa',lw=.8)
        ax.grid(alpha=.6,linestyle=':');ax.set_xlabel('Đổi về đông so nhánh 1 (″)',labelpad=11);ax.set_ylabel('Đổi về bắc (″)',labelpad=11)
        ax.legend(loc='upper left',bbox_to_anchor=(1.03,1.04),frameon=False,fontsize=9.5,labelspacing=1.2,handletextpad=.6)
        title='Bộ rộng · ảnh thật' if group['configuration']=='broad' else 'Bộ chặt · ảnh thật'
        fig.suptitle(title,x=.13,y=.97,va='top',ha='left',fontsize=18,fontweight='bold')
        fig.text(.13,.875,'Mũi tên nối hai ràng buộc trên cùng nền/ePSF.',va='top',fontsize=10,color='#c7d6e6')
        fig.text(.13,.045,'×: chưa qua sàng lọc số; không vẽ ellipse sai số.',fontsize=10,color='#c7d6e6')
        entry=save(fig,FOLDER/f"real-sensitivity-{group['configuration']}.svg")
        result['figures'].append({**entry,'role':'real_model_sensitivity','configuration':group['configuration'],
            'units':'arcsec','minimum_axis_span_arcsec':.1,'planned_pairs':8,'plotted_pairs':len(delta),
            'plotted_delta_east_north':{v:x.tolist() for v,x in delta.items()},
            'missing_variants':[v for v in VARIANTS if v not in delta]})
    points=[]
    for row in controls['paired_draws']:
        a=row['arms'][VARIANTS[0]];b=row['arms'][VARIANTS[1]]
        if a['completed'] and b['completed']:
            points.append({'case':row['case'],'draw':row['draw'],'free_error_arcsec':a['error_arcsec'],
                'nonnegative_error_arcsec':b['error_arcsec'],
                'both_numerically_supported':bool(a['numerical_support_both'] and b['numerical_support_both'])})
    fig,ax=plt.subplots(figsize=(9.5,5.8));fig.subplots_adjust(left=.13,bottom=.21,right=.65,top=.79)
    maximum=max([max(p['free_error_arcsec'],p['nonnegative_error_arcsec']) for p in points]+[.1])*1.08
    for i,case in enumerate(CASES):
        subset=[p for p in points if p['case']==case]
        if not subset:continue
        xs=[p['free_error_arcsec'] for p in subset];ys=[p['nonnegative_error_arcsec'] for p in subset]
        caption=f"{'Nền plane' if case.startswith('plane') else 'Nền bậc hai'} · {'300' if '300' in case else '600'} µJy"
        ax.scatter(xs,ys,s=44,color=COLORS[i],marker=('o','s','^','D')[i],alpha=.9,label=caption)
        failed=[p for p in subset if not p['both_numerically_supported']]
        if failed:ax.scatter([p['free_error_arcsec'] for p in failed],[p['nonnegative_error_arcsec'] for p in failed],s=28,marker='x',color='#fff',linewidth=1)
    ax.plot([0,maximum],[0,maximum],color='#d4dee8',ls='--',lw=1)
    ax.set_xlim(0,maximum);ax.set_ylim(0,maximum);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.6,linestyle=':')
    ax.set_xlabel('Sai lệch khi hàng xóm có dấu (″)',labelpad=11);ax.set_ylabel('Sai lệch khi hàng xóm không âm (″)',labelpad=11)
    ax.legend(loc='upper left',bbox_to_anchor=(1.03,1.04),frameon=False,fontsize=10,labelspacing=1.2)
    fig.suptitle('Đối chứng tổng hợp · cùng realization',x=.13,y=.97,va='top',ha='left',fontsize=17,fontweight='bold')
    fig.text(.13,.875,f'{len(points)}/64 cặp completed · ×: chưa cùng qua sàng lọc số',va='top',fontsize=10,color='#c7d6e6')
    fig.text(.13,.045,'Mọi cặp fit được, kể cả chưa qua sàng lọc số. Một geometry; noise oracle có điều kiện.',fontsize=9,color='#c7d6e6')
    entry=save(fig,FOLDER/'control-error-pairs.svg')
    result['figures'].append({**entry,'role':'all_common_completed_control_errors','units':'arcsec',
        'planned_paired_draws':64,'plotted_paired_draws':len(points),'points':points})
    (FOLDER/'figures.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'figures':len(result['figures']),'manifest_sha256':digest(FOLDER/'figures.json')}))


if __name__=='__main__':render()
