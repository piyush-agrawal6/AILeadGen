"""Rasterize every final sample page and make contact sheets for visual review."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
from PIL import Image,ImageDraw
poppler=Path(r'C:/Users/agraw/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
folder=Path('tmp/pdfs/phase36');folder.mkdir(parents=True,exist_ok=True)
def render(kind):
    root=folder.resolve()
    for previous in folder.glob(kind+'-*.png'):
        if previous.resolve().is_relative_to(root):previous.unlink()
    subprocess.run([str(poppler),'-scale-to','1100','-png',f'output/pdf/planebyte-phase36-{kind}.pdf',str(folder/kind)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    paths=sorted(folder.glob(kind+'-*.png'));pages=[]
    for p in paths:
        image=Image.open(p).convert('RGB');image.thumbnail((420,595));tile=Image.new('RGB',(440,625),'#ddd');tile.paste(image,((440-image.width)//2,10));ImageDraw.Draw(tile).text((12,605),p.name,fill='black');pages.append(tile)
    montage=Image.new('RGB',(440*min(5,len(pages)),625*((len(pages)+4)//5)),'#ddd')
    for i,image in enumerate(pages):montage.paste(image,((i%5)*440,(i//5)*625))
    montage.save(folder/(kind+'-montage.jpg'))
    return kind,len(paths)
with ThreadPoolExecutor(4) as pool:print(json.dumps(dict(pool.map(render,['reachable','mid-market','no-website','unreachable']))))
