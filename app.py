"""
Barcode Sheet Generator
-----------------------
Single file — NO templates folder needed.

Install:  pip install flask python-barcode reportlab pillow
Run:      python app.py
Open:     http://localhost:5050
"""

from flask import Flask, request, send_file, jsonify
import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Table, TableStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
import io, os, tempfile, base64

app = Flask(__name__)

# ──────────────────────────────────────────────────────────────
#  Embedded HTML  (no templates/ folder required)
# ──────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Barcode Sheet Generator</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f0f0f; --surface:#181818; --border:#2a2a2a;
  --accent:#e8f55a; --accent2:#5af5b8;
  --text:#f0f0f0; --muted:#666; --r:10px;
}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;
     min-height:100vh;display:flex;flex-direction:column;align-items:center}

header{width:100%;padding:26px 40px 18px;border-bottom:1px solid var(--border);
       display:flex;align-items:baseline;gap:14px}
header h1{font-size:1.45rem;font-weight:800;letter-spacing:-.02em}
header h1 span{color:var(--accent)}
header p{font-size:.75rem;color:var(--muted);font-family:'DM Mono',monospace}

.wrap{width:100%;max-width:900px;padding:32px 20px 60px;
      display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:620px){.wrap{grid-template-columns:1fr}.full{grid-column:1!important}}

.card{background:var(--surface);border:1px solid var(--border);
      border-radius:var(--r);padding:26px}
.card h2{font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;
         color:var(--accent);font-family:'DM Mono',monospace;margin-bottom:18px}
.full{grid-column:1/-1}

.field{margin-bottom:14px}
.field label{display:block;font-size:.7rem;color:var(--muted);margin-bottom:5px;
             font-family:'DM Mono',monospace;letter-spacing:.05em}
.field input,.field select{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;
  padding:9px 13px;color:var(--text);font-family:'DM Mono',monospace;
  font-size:.86rem;outline:none;transition:border-color .18s}
.field input:focus,.field select:focus{border-color:var(--accent)}
.field select option{background:#1a1a1a}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}

.btn{width:100%;padding:11px;border-radius:7px;border:none;font-family:'Syne',sans-serif;
     font-size:.86rem;font-weight:700;cursor:pointer;transition:all .18s;letter-spacing:.03em}
.btn-y{background:var(--accent);color:#0f0f0f;margin-top:10px}
.btn-y:hover{background:#d4e040;transform:translateY(-1px)}
.btn-g{background:transparent;color:var(--accent2);border:1px solid var(--accent2)}
.btn-g:hover{background:rgba(90,245,184,.07)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important}

#status{font-size:.73rem;font-family:'DM Mono',monospace;color:var(--muted);
        margin-top:11px;min-height:16px;text-align:center}
#status.err{color:#f55a5a}
#status.ok{color:var(--accent2)}

.preview-wrap{display:flex;flex-wrap:wrap;gap:12px;min-height:120px;
              align-items:center;justify-content:center}
.bc-box{background:#fff;border-radius:4px;padding:8px 10px;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 2px 8px rgba(0,0,0,.4)}
.bc-box img{max-height:110px;max-width:260px;object-fit:contain;display:block}
.ph{color:var(--muted);font-size:.78rem;font-family:'DM Mono',monospace;text-align:center}

.info-strip{margin-top:14px;padding-top:12px;border-top:1px solid var(--border);
            font-size:.7rem;color:var(--muted);font-family:'DM Mono',monospace}
.info-strip span{color:var(--text)}
</style>
</head>
<body>

<header>
  <h1>Barcode<span>Sheet</span></h1>
  <p>A4 label generator &mdash; Code128</p>
</header>

<div class="wrap">

  <div class="card">
    <h2>Series Settings</h2>
    <div class="field">
      <label>Prefix (optional)</label>
      <input id="prefix" type="text" placeholder="e.g. X000" maxlength="20"/>
    </div>
    <div class="row2">
      <div class="field">
        <label>Start Number</label>
        <input id="start" type="number" value="1" min="0"/>
      </div>
      <div class="field">
        <label>End Number</label>
        <input id="end" type="number" value="30" min="1"/>
      </div>
    </div>
    <div class="field">
      <label>Columns per row</label>
      <select id="cols">
        <option value="3" selected>3 per row</option>
        <option value="4">4 per row</option>
      </select>
    </div>
    <div id="status"></div>
  </div>

  <div class="card">
    <h2>Generate</h2>
    <p style="font-size:.76rem;color:var(--muted);font-family:'DM Mono',monospace;line-height:1.65;margin-bottom:16px">
      Preview one barcode instantly, or download a print-ready A4 PDF with the full series.
    </p>
    <button class="btn btn-g" onclick="previewOne()">Preview Sample</button>
    <button class="btn btn-y" id="pdfBtn" onclick="makePDF()">&#11015; Download A4 PDF</button>
    <div class="info-strip">
      Total: <span id="tot">30</span> barcodes &nbsp;&middot;&nbsp;
      Layout: <span id="lay">3 &times; 10 rows</span>
    </div>
  </div>

  <div class="card full">
    <h2>Preview</h2>
    <div class="preview-wrap" id="prev">
      <span class="ph">Click "Preview Sample" to see a barcode</span>
    </div>
  </div>

</div>

<script>
const $=id=>document.getElementById(id)
function vals(){
  return{
    prefix:$('prefix').value.trim(),
    start:parseInt($('start').value)||1,
    end:parseInt($('end').value)||30,
    cols:parseInt($('cols').value)
  }
}
function updateInfo(){
  const{start,end,cols}=vals()
  const total=Math.max(0,end-start+1)
  $('tot').textContent=total
  $('lay').textContent=cols+' x '+Math.ceil(total/cols)+' rows'
}
['start','end','cols','prefix'].forEach(id=>$(id).addEventListener('input',updateInfo))
updateInfo()

function setStatus(msg,type=''){const el=$('status');el.textContent=msg;el.className=type}

async function previewOne(){
  const{prefix,start}=vals()
  const num=prefix+start
  setStatus('Generating...')
  try{
    const r=await fetch('/preview',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({number:num})
    })
    const d=await r.json()
    if(d.error){setStatus(d.error,'err');return}
    $('prev').innerHTML='<div class="bc-box"><img src="'+d.image+'" alt="barcode"/></div>'
    setStatus('Sample: '+num,'ok')
  }catch(e){setStatus('Error: '+e.message,'err')}
}

async function makePDF(){
  const{prefix,start,end,cols}=vals()
  if(end<start){setStatus('End must be >= Start','err');return}
  if(end-start+1>500){setStatus('Max 500 barcodes','err');return}
  const btn=$('pdfBtn')
  btn.disabled=true; btn.textContent='Building PDF...'
  setStatus('Please wait...')
  try{
    const r=await fetch('/generate_pdf',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prefix,start,end,cols})
    })
    if(!r.ok){const d=await r.json();setStatus(d.error||'Server error','err');return}
    const blob=await r.blob()
    const url=URL.createObjectURL(blob)
    const a=document.createElement('a')
    a.href=url; a.download='barcodes_'+start+'_to_'+end+'.pdf'; a.click()
    URL.revokeObjectURL(url)
    setStatus('Downloaded '+(end-start+1)+' barcodes','ok')
  }catch(e){setStatus('Error: '+e.message,'err')}
  finally{btn.disabled=false; btn.textContent='Download A4 PDF'}
}
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
#  Barcode options — high DPI, tall bars, proper text gap
#  All values tuned so number text never overlaps the bars
# ──────────────────────────────────────────────────────────────
BARCODE_OPTIONS = {
    'module_height':  18.0,   # tall bars  → easy for phone cameras to read
    'module_width':   0.38,   # wide bars  → sharp at 300 dpi
    'quiet_zone':     6.5,    # white side margins (required by Code128 spec)
    'font_size':      11,     # clear, readable number below bars
    'text_distance':  6.0,    # gap between bottom of bars and number text
    'background':     'white',
    'foreground':     'black',
    'write_text':     True,
    'dpi':            300,    # high resolution — crisp print & reliable scan
}


def make_barcode(text: str) -> io.BytesIO:
    buf = io.BytesIO()
    bc  = barcode.get_barcode_class('code128')(text, writer=ImageWriter())
    bc.write(buf, options=BARCODE_OPTIONS)
    buf.seek(0)
    return buf


# ──────────────────────────────────────────────────────────────
#  Routes
# ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return HTML


@app.route('/preview', methods=['POST'])
def preview():
    number = (request.json or {}).get('number', '').strip()
    if not number:
        return jsonify({'error': 'No number provided'}), 400
    try:
        encoded = base64.b64encode(make_barcode(number).read()).decode()
        return jsonify({'image': f'data:image/png;base64,{encoded}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.json or {}
    try:
        start  = int(data.get('start', 1))
        end    = int(data.get('end', 30))
        prefix = data.get('prefix', '').strip()
        cols   = max(1, min(4, int(data.get('cols', 3))))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid input'}), 400

    if end < start:
        return jsonify({'error': 'End must be >= Start'}), 400
    if end - start + 1 > 500:
        return jsonify({'error': 'Max 500 barcodes at once'}), 400

    pad     = len(str(end))
    numbers = [f"{prefix}{str(i).zfill(pad)}" for i in range(start, end + 1)]

    # write PNGs to temp dir
    tmpdir = tempfile.mkdtemp()
    files  = []
    for num in numbers:
        path = os.path.join(tmpdir, f"{num}.png")
        with open(path, 'wb') as f:
            f.write(make_barcode(num).read())
        files.append(path)

    # ── PDF layout ──
    # cell_h is tall enough to hold: bars + text_distance + number text + padding
    # With module_height=18mm, text_distance=6mm, font~4mm → need ~32mm cell minimum
    margin    = 10 * mm
    page_w, _ = A4
    usable_w  = page_w - 2 * margin
    cell_w    = usable_w / cols
    cell_h    = 34 * mm    # bars + gap + number + breathing room — zero overlap
    img_w     = cell_w - 6 * mm
    img_h     = cell_h - 4 * mm

    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin,  bottomMargin=margin,
    )

    table_rows, row = [], []
    for path in files:
        row.append(RLImage(path, width=img_w, height=img_h))
        if len(row) == cols:
            table_rows.append(row)
            row = []
    if row:
        while len(row) < cols:
            row.append('')
        table_rows.append(row)

    tbl = Table(
        table_rows,
        colWidths=[cell_w] * cols,
        rowHeights=[cell_h] * len(table_rows),
    )
    tbl.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ]))

    doc.build([tbl])
    pdf_buf.seek(0)

    for f in files:
        os.remove(f)
    os.rmdir(tmpdir)

    return send_file(
        pdf_buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'barcodes_{start}_to_{end}.pdf',
    )


if __name__ == '__main__':
    app.run(debug=True, port=5050)
