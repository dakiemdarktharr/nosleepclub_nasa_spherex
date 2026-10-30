"""Render model-sensitivity figures from the completed, opened-data study.

Optional offline dependencies live in requirements-figures.txt. This script
neither optimizes an estimator nor draws a confidence/detection contour.
"""
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


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/raw/benchmark/linked-wise-development.json'
SOURCE_SHA = 'a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a'
OUT = ROOT/'web/data/linked-flux'
LABELS = (
    ('independent', '1  Độ sáng riêng', 'o', '#eef3fa'),
    ('shared_r7_68_a0', '2  Độ sáng theo phổ', 's', '#ffa75c'),
    ('tilt_r7_68_a0', '3  Phổ + độ nghiêng', 'D', '#a0b8ff'),
    ('shared_r7_68_am4', '4  Reference α = −4', '^', '#57d5c5'),
    ('shared_r7_68_ap4', '5  Reference α = +4', 'v', '#f6d86e'),
    ('shared_qr2_68_a0', '6  Center QR2', 'P', '#e89edb'),
    ('shared_r7_17_a0', '7  Response 17 kênh', 'X', '#80c6ff'),
)


def render():
    raw = SOURCE.read_bytes()
    if sha256(raw).hexdigest() != SOURCE_SHA:
        raise RuntimeError('completed study checksum differs')
    data = json.loads(raw)
    if not data['completed'] or data['counts']['fit_completed'] != 28 or len(data['pairs']) != 14:
        raise RuntimeError('figure requires the complete 28-attempt development study')
    plt.rcParams.update({
        'font.family':'DejaVu Sans', 'font.size':12,
        'figure.facecolor':'#111923', 'axes.facecolor':'#111923',
        'axes.edgecolor':'#8b9aaa', 'text.color':'#eef3fa',
        'axes.labelcolor':'#eef3fa', 'xtick.color':'#dce5ef',
        'ytick.color':'#dce5ef', 'grid.color':'#455466',
        'svg.hashsalt':'wise-linked-development-1', 'svg.fonttype':'path',
    })
    texts = [x[1] for x in LABELS] + [
        'Thay đổi về đông so nhánh 1 (″)', 'Thay đổi về bắc (″)',
        'Rộng · 10 ảnh mỗi epoch', 'Chặt · 2 ảnh mỗi epoch',
        '3 trùng 1', '4, 5, 7 sát 2', '4, 5, 6, 7 sát 2',
        'Các điểm biểu diễn giả định mô hình; chưa đo độ chính xác.',
    ]
    font_path = font_manager.findfont('DejaVu Sans', fallback_to_default=False)
    glyphs = FT2Font(font_path).get_charmap()
    missing = {c for text in texts for c in text if not c.isspace() and ord(c) not in glyphs}
    if missing:
        raise RuntimeError('plot font lacks glyphs: '+repr(sorted(missing)))
    manifest = {
        'version':'0.10.0-linked-figures.1', 'source_sha256':SOURCE_SHA,
        'source_bytes':len(raw), 'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependency_manifest_sha256':sha256((ROOT/'requirements-figures.txt').read_bytes()).hexdigest(),
        'packages':{n:version(n) for n in ('matplotlib','numpy','Pillow','fonttools')},
        'font':{'family':'DejaVu Sans','sha256':sha256(Path(font_path).read_bytes()).hexdigest(),
                'glyph_check':'all plotted Vietnamese and mathematical glyphs present'},
        'quantity':'difference of east/north displacement vectors from independent control, arcsec',
        'qualification':'Opened-data model sensitivity; no uncertainty ellipse, validation, accuracy or detection claim.',
        'figures':[],
    }
    for configuration, title in (('broad','Rộng · 10 ảnh mỗi epoch'),('strict','Chặt · 2 ảnh mỗi epoch')):
        pairs = {r['variant']:r for r in data['pairs'] if r['configuration']==configuration}
        control = np.asarray(pairs['independent']['east_north_arcsec'], float)
        delta = {name:np.asarray(pairs[name]['east_north_arcsec'],float)-control for name,*_ in LABELS}
        fig, ax = plt.subplots(figsize=(9,5.6))
        fig.subplots_adjust(left=.13,bottom=.19,right=.66,top=.80)
        for name, label, marker, color in LABELS:
            x,y = delta[name]
            ax.annotate('', xy=(x,y),xytext=(0,0),
                        arrowprops={'arrowstyle':'->','color':color,'lw':1,'alpha':.7})
            ax.scatter([x],[y],s=72,marker=marker,facecolor='none',edgecolor=color,
                       linewidth=1.7,label=label,zorder=3)
        # Coincident points remain in the figure and table; labels explain the overlap.
        if configuration=='broad':
            for name, label, offset in (
                ('independent','1',(8,9)),('shared_r7_68_a0','2',(9,-16)),
                ('tilt_r7_68_a0','3',(8,8)),('shared_qr2_68_a0','6',(9,8))):
                ax.annotate(label,delta[name],xytext=offset,textcoords='offset points',fontsize=12)
            overlap='4, 5, 7 sát 2'
        else:
            ax.annotate('1, 3',delta['independent'],xytext=(9,-17),textcoords='offset points')
            ax.annotate('2, 4, 5, 6, 7',delta['shared_r7_68_a0'],xytext=(10,0),textcoords='offset points')
            overlap='3 trùng 1; 4, 5, 6, 7 sát 2'
        ax.axhline(0,color='#8b9aaa',lw=.8,alpha=.8)
        ax.axvline(0,color='#8b9aaa',lw=.8,alpha=.8)
        ax.grid(alpha=.6,linestyle=':')
        ax.set_xlabel('Thay đổi về đông so nhánh 1 (″)',labelpad=12)
        ax.set_ylabel('Thay đổi về bắc (″)',labelpad=12)
        ax.set_aspect('equal',adjustable='datalim')
        ax.margins(.27)
        ax.legend(loc='upper left',bbox_to_anchor=(1.03,1.02),frameon=False,
                  labelspacing=1.2,fontsize=11,handletextpad=.7)
        fig.suptitle(title,x=.13,y=.97,ha='left',va='top',fontsize=18,fontweight='bold')
        fig.text(.13,.875,overlap,va='top',fontsize=11,color='#c7d6e6')
        fig.text(.13,.045,'Các điểm biểu diễn giả định mô hình; chưa đo độ chính xác.',fontsize=10,color='#c7d6e6')
        path=OUT/f'sensitivity-{configuration}.svg'
        fig.savefig(path,format='svg',metadata={'Date':None,'Creator':'Matplotlib; scripts.plot_linked_study'})
        # Match the repository's LF contract on Windows before hashing/export.
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
        plt.close(fig)
        manifest['figures'].append({'configuration':configuration,'path':path.relative_to(ROOT/'web').as_posix(),
            'sha256':sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,
            'values_arcsec':{name:value.tolist() for name,value in delta.items()}})
    target=OUT/'figures.json'
    target.write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'figures':len(manifest['figures']),'manifest':str(target),
                      'sha256':sha256(target.read_bytes()).hexdigest()},ensure_ascii=False))


if __name__=='__main__':
    render()
