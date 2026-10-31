"use strict";

const menuButton=$("menu-toggle"), navigation=$("main-nav");
menuButton.addEventListener("click",()=>{
  const open=menuButton.getAttribute("aria-expanded")!=="true";
  menuButton.setAttribute("aria-expanded",String(open));navigation.classList.toggle("open",open);
});
navigation.querySelectorAll("a").forEach(link=>link.addEventListener("click",()=>{
  navigation.classList.remove("open");menuButton.setAttribute("aria-expanded","false");
}));
function navigationState(){navigation.querySelectorAll("a").forEach(a=>{const active=a.hash===(location.hash||"#home");a.classList.toggle("active",active);if(active)a.setAttribute("aria-current","location");else a.removeAttribute("aria-current");});}
window.addEventListener("hashchange",navigationState);navigationState();
const guide=$("guide-dialog");
for(const dialog of [guide,$("evidence-dialog")])dialog.addEventListener("keydown",event=>{
  if(event.key!=="Tab"||event.altKey||event.ctrlKey||event.metaKey)return;
  const items=[...dialog.querySelectorAll('button,a[href],input,select,textarea,[tabindex]')].filter(node=>node.tabIndex>=0&&!node.disabled&&node.getClientRects().length);
  if(!items.length)return;
  const first=items[0],last=items[items.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
});
document.addEventListener("keydown",event=>{if(event.key==="Escape"&&menuButton.getAttribute("aria-expanded")==="true"){navigation.classList.remove("open");menuButton.setAttribute("aria-expanded","false");menuButton.focus();}});
[$("guide-open"),$("workspace-help")].forEach(button=>button.addEventListener("click",()=>{window.SkyApp?.pause();window.SkyExplorer?.pause();guide.showModal();}));
$("guide-close").addEventListener("click",()=>guide.close());
$("guide-start").addEventListener("click",()=>{guide.close();if(window.SkyWorkflow)window.SkyWorkflow.openCompare();else{location.hash="workspace";canvas.focus({preventScroll:true});}});
$("scene-select").addEventListener("change",()=>{
  const scene=state.manifest?.scenes.find(s=>s.id===$("scene-select").value);
  if(scene)loadScene(scene);
});
document.addEventListener("scene:loaded",()=>{
  const select=$("scene-select"),s=state.scene;
  const custom=select.querySelector("[data-legacy]");if(custom)custom.remove();
  if(![...select.options].some(o=>o.value===s.id)) {
    const option=document.createElement("option");option.value=s.id;option.textContent=s.label;option.dataset.legacy="true";select.append(option);
  }
  select.value=s.id;$("hero-baseline").textContent=`${number(s.baseline_days,1)} ngày`;
});
$("privacy-open").addEventListener("click",()=>{
  $("evidence-content").innerHTML=`<h3>Nhận xét của phiên trình duyệt này</h3><p>Nút Lưu nhận xét ghi vào MongoDB khi máy chủ sẵn sàng. Cookie HttpOnly xác định phiên; không có tài khoản hoặc đồng bộ giữa thiết bị. Phiên khác không xem được nhận xét của bạn.</p><p>Nhận xét hết hạn sau 180 ngày. Bạn có thể xóa từng nhận xét hoặc xuất JSON. Nếu API lỗi, bản cục bộ vẫn được giữ và giao diện báo “Chưa đồng bộ”. Dữ liệu cũ trong trình duyệt không tự được gửi lên máy chủ.</p>`;
  $("download-fits").href=state.scene?.fits||"data/manifest.json";$("evidence-dialog").showModal();
});

let releasePayloads=[];
function releaseTable() {
  if(!releasePayloads.length)return;
  const config=releasePayloads.find(p=>p.result.spectral_configuration===$("release-spectrum").value);
  const groups=config.result.groups.filter(g=>g.truth_psf===$("release-truth").value&&g.model!=="single_nearest");
  $("release-rows").innerHTML=groups.map(g=>{
    const baseline=config.result.groups.find(b=>b.model==="single_nearest"&&b.truth_psf===g.truth_psf&&b.flux_scale===g.flux_scale);
    return `<tr><td>${g.model==="ir_nearest"?"IR + ePSF gần nhất":"IR + ePSF nội suy"}</td><td>${number(g.flux_scale,1)}×</td><td>${number(g.paired_baseline_rms_arcsec,2)}″ / <strong>${number(g.paired_model_rms_arcsec,2)}″</strong></td><td>${g.paired_valid}/${g.attempted}</td><td>${baseline.valid}/${baseline.attempted} · ${g.valid}/${g.attempted}</td><td>${number(g.rms_arcsec,2)}″</td><td>${g.within_68_ellipse}/${g.attempted}</td></tr>`;
  }).join("");
}
function releasePassed() {
  return ["ir_nearest","ir_bilinear"].filter(model=>releasePayloads.every(p=>p.result.groups.filter(g=>g.model===model).every(g=>{
    const baseline=p.result.groups.find(b=>b.model==="single_nearest"&&b.truth_psf===g.truth_psf&&b.flux_scale===g.flux_scale);
    return g.paired_model_rms_arcsec<g.paired_baseline_rms_arcsec&&g.valid>=baseline.valid;
  })));
}
async function setupRelease() {
  try {
    releasePayloads=await Promise.all([getJson("data/release/broad.json"),getJson("data/release/strict.json")]);
    const protocol=await getJson("data/release/overview.json");
    $("ir-source-count").textContent=number(protocol.catalog_screening.selected,0);
    $("patch-overlay").innerHTML=protocol.positions_px.map(([x,y],i)=>`<g><circle cx="${x+64.5}" cy="${192-y-64.5}" r="3.2" fill="none" stroke="#ffb36a" stroke-width=".65"/><text x="${x+68}" y="${192-y-65}" fill="#fff" stroke="#000" stroke-width=".6" paint-order="stroke" font-size="3.3">${i+1}</text></g>`).join("");
    const passed=releasePassed();
    $("release-verdict").textContent=passed.length?"Qua gate điểm ước lượng · cần kiểm chứng thêm":"Chưa giảm sai lệch ổn định";
    releaseTable();
  } catch {$("release-verdict").textContent="Chưa tải được kết quả";$("release-rows").innerHTML='<tr><td colspan="7">Tải lại trang để lấy kết quả kiểm chứng.</td></tr>';}
  finally {$("release-validation").removeAttribute("aria-busy");}
}
[$("release-spectrum"),$("release-truth")].forEach(select=>select.addEventListener("change",releaseTable));
$("release-evidence").addEventListener("click",()=>{
  if(!releasePayloads.length)return;
  $("evidence-content").innerHTML=`<h3>30 vùng mới, cấu hình khóa trước</h3><p>Cấu hình 0.5.0 được khóa ở commit <code>581de33</code> trước khi fit mục tiêu và tiêm nguồn. 30 stamp tách nhau ít nhất 20 pixel lưới trời và cách các vị trí thử cũ ít nhất 20 pixel. Chỉ dùng hình học và mặt nạ hợp lệ để chọn vùng, không chọn theo kết quả phục hồi.</p><p>Catalog CatWISE2020: 5.078 nguồn truy vấn, 1.783 nguồn qua điều kiện IR; 508 nguồn lấy vị trí Gaia đã lan truyền. Nguồn còn lại dùng vị trí/chuyển động CatWISE với hiệu chỉnh tile chính thức. Cắt W2 ≤16, S/N ≥10, chi² ≤2, artifact 00 và chuyển động lớn; không dùng độ sáng catalog để buộc flux SPHEREx.</p><p>Ba mô hình: một nguồn/ePSF gần nhất; nhiều nguồn IR/ePSF gần nhất; nhiều nguồn IR/ePSF nội suy. Giữ cùng pixel, noise map và solver; chỉ fit centroid mục tiêu, với biên độ nguồn và mặt phẳng nền riêng từng exposure. Không buộc chuyển động theo dự báo ngoài.</p><p>Hai độ sáng × đứng yên/dịch chuyển × hai hình nguồn tiêm × 30 vùng. Tiêm bằng cả ePSF gần nhất và nội suy để kiểm tra mismatch. 1.440 phép phục hồi qua hai cấu hình phổ và ba mô hình, cộng bootstrap noise 128 lượt/epoch. Không thêm shot noise nguồn. 30 vùng đều ở cùng một trường, chia sẻ exposure: không phải 30 survey độc lập.</p><p>Bảng chính so RMS trên các lượt cùng fit hợp lệ; số fit hợp lệ và ellipse giữ mẫu số mọi lượt thử. Ngân sách ellipse ở phép thử chỉ bao gồm noise mô hình có điều kiện; còn thiếu sai số vị trí hàng xóm, ePSF, phổ và detector. Không dùng tỷ lệ này như xác suất phát hiện hay completeness.</p><p>QR3: SIA và TAP đều không tìm thấy ảnh tại tọa độ đã truy vấn. Vì vậy đây là kiểm tra độ phủ QR3/QR2, chưa phải so hai ảnh cùng exposure. Bản phân tích vẫn dùng QR2 với calibration ePSF chính thức; không giả lập ảnh QR3.</p><div class="evidence-table"><table><thead><tr><th>Phổ</th><th>Mô hình</th><th>Đông / Bắc</th><th>Độ dài</th><th>σ noise</th></tr></thead><tbody>${releasePayloads.map(p=>Object.entries(p.result.models).map(([name,m])=>`<tr><td>${p.result.spectral_configuration}</td><td>${name}</td><td>${number(m.east_arcsec,2)}″ / ${number(m.north_arcsec,2)}″</td><td>${number(m.displacement_arcsec,2)}″</td><td>${number(m.noise_radial_arcsec,2)}″</td></tr>`).join("")).join("")}</tbody></table></div><p>σ ở bảng là noise có điều kiện, không phải ngân sách hệ thống đầy đủ và không so trực tiếp với σ tổng bản Gaia 0.3.0. Thí nghiệm không tự thay số đo mặc định.</p><p><a href="data/release/protocol.json" download>Cấu hình, nguồn và hash đã khóa</a> · <a href="https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html" target="_blank" rel="noopener noreferrer">CatWISE: định nghĩa và hiệu chỉnh</a> · <a href="https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/" target="_blank" rel="noopener noreferrer">ePSF chính thức</a></p>`;
  $("evidence-content").insertAdjacentHTML("beforeend",`<p>RMS là độ lệch điển hình; nhỏ hơn là tốt hơn. Cặp hợp lệ là các lượt mà cả mô hình cũ và mới đều fit được. Vì mô hình mới cứu thêm một số fit trước đây chạm biên, xem cả RMS mọi fit mới và cột số fit, không chỉ RMS ghép cặp.</p><p>Frame căn chỉnh giữ nguyên bản Gaia 0.3.0; chưa fit lại sao tham chiếu với ePSF nội suy. Khoảng bootstrap theo vùng còn rộng: ví dụ phổ rộng, nguồn 0,5×, tiêm ePSF gần nhất, IR+nội suy giảm điểm ước lượng 36,8%, nhưng khoảng chẩn đoán 95% là −31,4% đến +64,2%. Chưa chứng minh cải thiện tổng quát.</p><p><a href="data/release/summary.json" download>So sánh ghép cặp và bootstrap theo vùng</a> · <a href="https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/blob/main/docs/QR3_CATWISE_VALIDATION.md" target="_blank" rel="noopener noreferrer">Báo cáo, cách tái tạo và bước tiếp theo</a></p>`);
  $("download-fits").href=state.scene?.fits||"data/manifest.json";$("evidence-dialog").showModal();
});
setupRelease();

function sizeMapLabels(map) {
  const width=map.getBoundingClientRect().width;
  if(width<=0)return;
  const scale=192/width;
  map.querySelectorAll("svg text").forEach(text=>{
    text.style.fontSize=`${12*scale}px`;
    text.style.stroke="#050a11";
    text.style.strokeWidth=`${3*scale}px`;
    text.style.paintOrder="stroke";
  });
}
const mapLabelSizing=new ResizeObserver(entries=>entries.forEach(entry=>sizeMapLabels(entry.target)));
document.querySelectorAll(".reference-map").forEach(map=>{
  mapLabelSizing.observe(map);
  new MutationObserver(()=>sizeMapLabels(map)).observe(map,{childList:true,subtree:true});
});
