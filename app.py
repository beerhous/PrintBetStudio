<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PrintBet Studio Enterprise</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f8fafc; user-select: none; }
        .receipt-paper { background: #fff; font-family: 'Consolas', monospace; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; min-height: 400px; font-size: 12px; line-height: 1.5; }
        .omr-mark { background: #000; color: #fff; padding: 0 3px; font-weight: bold; border-radius: 2px; }
        .modal { transition: opacity 0.2s ease-in-out; pointer-events: none; opacity: 0; }
        .modal.open { pointer-events: auto; opacity: 1; }
        .tab-btn.active { background: #3b82f6; color: white; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.5); }
        .settings-nav-item.active { border-left-color: #3b82f6; color: #3b82f6; background: #eff6ff; }
        .ball { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; border-radius: 50%; cursor: pointer; font-weight: bold; color: #475569; transition: all 0.1s; background: white; }
        .ball.active { background: #ef4444; color: white; border-color: #ef4444; box-shadow: 0 2px 4px rgba(239,68,68,0.3); }
        .ball.rect { border-radius: 6px; width: auto; padding: 0 16px; height: 36px; font-size: 13px; }
        .ball.rect.active { background: #22c55e; color: white; border-color: #22c55e; box-shadow: 0 2px 4px rgba(34,197,94,0.3); }

        /* === 新增：Toast 通知容器 === */
        #toast-container { position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; pointer-events: none; }
        .toast { pointer-events: auto; min-width: 300px; padding: 16px; border-radius: 8px; background: white; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); display: flex; align-items: center; gap: 12px; animation: slideIn 0.3s ease-out; border-left: 5px solid; }
        .toast.error { border-left-color: #ef4444; }
        .toast.success { border-left-color: #22c55e; }
        .toast.info { border-left-color: #3b82f6; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
    </style>
</head>
<body class="h-screen flex flex-col text-slate-800">

    <!-- Toast 容器 -->
    <div id="toast-container"></div>

    <!-- 1. 顶部导航 -->
    <header class="bg-slate-900 text-white h-16 flex items-center px-6 justify-between shadow-lg z-30">
        <div class="flex items-center gap-3 font-bold text-xl tracking-wide">
            <div class="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center text-sm shadow-inner"><i class="fa-solid fa-print"></i></div>
            PrintBet Studio
        </div>
        <div class="flex bg-slate-800 p-1.5 rounded-xl gap-1 shadow-inner border border-slate-700">
            <button onclick="switchMode('football')" id="tab-football" class="tab-btn active px-5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2"><i class="fa-regular fa-futbol"></i> 竞彩足球</button>
            <button onclick="switchMode('basketball')" id="tab-basketball" class="tab-btn px-5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2"><i class="fa-solid fa-basketball"></i> 竞彩篮球</button>
            <button onclick="switchMode('number')" id="tab-number" class="tab-btn px-5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2"><i class="fa-solid fa-ticket"></i> 数字彩票</button>
        </div>
        <div class="flex items-center gap-5">
            <div class="flex flex-col items-end text-[10px] text-slate-400 font-mono leading-tight cursor-help" title="硬件连接状态">
                <div class="flex items-center gap-1.5">OCR <span class="w-2 h-2 rounded-full bg-gray-500 transition-colors" id="led-ocr"></span></div>
                <div class="flex items-center gap-1.5">PRN <span class="w-2 h-2 rounded-full bg-gray-500 transition-colors" id="led-prn"></span></div>
            </div>
            <button onclick="openSettings()" class="w-9 h-9 rounded-full hover:bg-slate-700 flex items-center justify-center transition text-slate-300 hover:text-white border border-transparent hover:border-slate-600">
                <i class="fa-solid fa-gear text-lg"></i>
            </button>
        </div>
    </header>

    <!-- 2. 主内容区 -->
    <div class="flex-1 flex overflow-hidden">
        <main class="flex-1 flex flex-col bg-white border-r border-slate-200 relative z-10">
            <div class="h-16 border-b border-slate-100 flex items-center justify-between px-6 bg-slate-50/50 backdrop-blur-sm">
                <div class="flex gap-4 items-center" id="global-config-area">
                    <div class="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
                        <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Pass</label>
                        <select id="passType" class="text-sm font-bold text-slate-700 bg-transparent outline-none w-24 cursor-pointer hover:text-blue-600">
                            <option value="1x1">单关</option><option value="2x1">2串1</option><option value="3x1">3串1</option><option value="4x1">4串1</option><option value="5x1">5串1</option><option value="6x1">6串1</option>
                        </select>
                    </div>
                    <div class="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
                        <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Multi</label>
                        <input type="number" id="multiplier" value="10" class="text-sm font-bold text-blue-600 bg-transparent outline-none w-12 text-center hover:bg-blue-50 rounded transition">
                    </div>
                </div>
                <button onclick="startOCR()" class="text-slate-500 hover:text-blue-600 text-sm font-bold flex items-center gap-2 transition px-4 py-2 rounded-lg hover:bg-blue-50 border border-transparent hover:border-blue-100">
                    <i class="fa-solid fa-camera"></i> 截图识别
                </button>
            </div>
            <div class="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 text-[10px] font-bold text-slate-400 uppercase border-b border-slate-200 tracking-wider">
                <div class="col-span-2">Match ID</div>
                <div class="col-span-2">Play Type</div>
                <div class="col-span-7">Selection</div>
                <div class="col-span-1 text-right">Action</div>
            </div>
            <div id="ticket-rows" class="flex-1 overflow-y-auto px-6 py-4 space-y-3 bg-slate-50/30"></div>
            <div class="p-6 border-t border-slate-100 bg-white shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] flex flex-col gap-4 z-20">
                <button onclick="addNewRow()" class="w-full border-2 border-dashed border-slate-300 rounded-xl py-3 text-slate-400 hover:border-blue-500 hover:text-blue-500 transition font-bold text-sm flex items-center justify-center gap-2 group">
                    <i class="fa-solid fa-plus group-hover:rotate-90 transition-transform"></i> 添加比赛 / 号码
                </button>
                <div class="flex items-center justify-between pt-2">
                    <div>
                        <div class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Estimated Cost</div>
                        <div class="text-3xl font-bold text-slate-800 leading-none mt-1">¥ <span id="total-amount">0</span></div>
                    </div>
                    <button onclick="doPrint()" class="bg-blue-600 hover:bg-blue-700 text-white px-10 py-3.5 rounded-xl font-bold shadow-lg shadow-blue-600/30 transition transform active:scale-95 flex items-center gap-3 text-lg">
                        <i class="fa-solid fa-print"></i> 立即出票
                    </button>
                </div>
            </div>
        </main>
        <aside class="w-[400px] bg-slate-100 border-l border-slate-200 flex flex-col shadow-inner">
            <div class="p-4 border-b border-slate-200 bg-white flex justify-between items-center shadow-sm z-10">
                <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2"><i class="fa-solid fa-eye"></i> Terminal Preview</h3>
                <div class="text-[10px] text-slate-300 font-mono" id="preview-time">--:--</div>
            </div>
            <div class="flex-1 p-8 overflow-y-auto flex justify-center bg-slate-200/50">
                <div class="receipt-paper w-full flex flex-col rounded-sm relative">
                    <div class="absolute left-2 top-1/2 -translate-y-1/2 flex flex-col gap-2">
                        <div class="w-2 h-2 rounded-full bg-slate-200"></div><div class="w-2 h-2 rounded-full bg-slate-200"></div><div class="w-2 h-2 rounded-full bg-slate-200"></div>
                    </div>
                    <div class="text-center font-bold text-base mb-1">PrintBet OMR</div>
                    <div class="text-center text-[10px] text-slate-400 mb-6 border-b border-dashed border-slate-300 pb-3">Official Simulation</div>
                    <div class="flex-1 flex items-center justify-center min-h-[200px] bg-slate-50 border border-dashed border-slate-200 rounded p-2 mb-4">
                        <img id="omr-preview-img" class="w-full opacity-90 mix-blend-multiply" alt="OMR Preview" style="display:none;">
                        <span id="omr-placeholder" class="text-xs text-slate-300 flex flex-col items-center gap-2"><i class="fa-solid fa-file-lines text-2xl"></i> 等待数据...</span>
                    </div>
                    <div class="border-t border-dashed border-slate-300 mt-2 pt-4">
                        <div class="text-center font-bold text-xs mb-3 text-slate-500">Scan to Terminal:</div>
                        <div id="qrcode" class="flex justify-center p-3 bg-white border border-slate-200 rounded-lg shadow-sm mx-auto w-fit"></div>
                    </div>
                </div>
            </div>
        </aside>
    </div>

    <!-- 设置 Modal (与之前一致) -->
    <div id="settings-modal" class="modal fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center backdrop-blur-sm hidden">
        <div class="bg-white rounded-2xl shadow-2xl w-[750px] h-[550px] flex overflow-hidden">
            <div class="w-56 bg-slate-50 border-r border-slate-200 py-6 flex flex-col">
                <div class="px-6 mb-6 text-xs font-bold text-slate-400 uppercase tracking-widest">Settings</div>
                <div class="settings-nav-item active" id="nav-hardware" onclick="switchSettingsTab('hardware')"><i class="fa-solid fa-plug w-5 mr-2"></i> 硬件连接</div>
                <div class="settings-nav-item" id="nav-prefs" onclick="switchSettingsTab('prefs')"><i class="fa-solid fa-sliders w-5 mr-2"></i> 操作偏好</div>
                <div class="settings-nav-item" id="nav-system" onclick="switchSettingsTab('system')"><i class="fa-solid fa-circle-info w-5 mr-2"></i> 系统更新</div>
            </div>
            <div class="flex-1 flex flex-col bg-white">
                <div class="h-16 border-b flex items-center justify-between px-8">
                    <span class="font-bold text-slate-800 text-xl">配置面板</span>
                    <button onclick="closeSettings()" class="text-slate-400 hover:text-red-500 transition"><i class="fa-solid fa-times text-xl"></i></button>
                </div>
                <div class="flex-1 p-8 overflow-y-auto relative">
                    <div id="panel-hardware" class="settings-panel block">
                        <div class="space-y-8">
                            <div class="bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 transition shadow-sm">
                                <label class="block text-sm font-bold text-slate-700 mb-3 flex items-center gap-2"><i class="fa-solid fa-print text-blue-500"></i> 热敏打印机</label>
                                <div class="flex gap-3"><select id="cfg-printer" class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm outline-none bg-slate-50"></select><button onclick="testPrinter()" class="bg-white border border-slate-200 px-5 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-50 hover:text-blue-600 hover:border-blue-200 transition whitespace-nowrap">测试打印</button></div>
                            </div>
                            <div class="bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 transition shadow-sm">
                                <label class="block text-sm font-bold text-slate-700 mb-3 flex items-center gap-2"><i class="fa-solid fa-eye text-blue-500"></i> OCR 接口地址</label>
                                <div class="flex gap-3"><input id="cfg-ocr" type="text" class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm outline-none font-mono text-slate-600"><button onclick="testOCR()" class="bg-white border border-slate-200 px-5 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-50 hover:text-blue-600 hover:border-blue-200 transition whitespace-nowrap">测试连接</button></div>
                            </div>
                        </div>
                    </div>
                    <div id="panel-prefs" class="settings-panel hidden">
                         <div class="bg-slate-50 p-5 rounded-xl border border-slate-200">
                            <label class="block text-sm font-bold text-slate-700 mb-3">默认过关方式</label>
                            <select id="cfg-pass" class="w-full border border-slate-300 rounded-lg px-4 py-2.5 text-sm outline-none bg-white"><option>2x1</option><option>3x1</option></select>
                        </div>
                        <div class="mt-4 bg-slate-50 p-5 rounded-xl border border-slate-200">
                            <label class="block text-sm font-bold text-slate-700 mb-3">默认倍数</label>
                            <input id="cfg-multi" type="number" class="w-full border border-slate-300 rounded-lg px-4 py-2.5 text-sm outline-none bg-white">
                        </div>
                    </div>
                    <div id="panel-system" class="settings-panel hidden text-center pt-8">
                        <div class="w-20 h-20 bg-gradient-to-br from-slate-100 to-slate-200 rounded-2xl flex items-center justify-center mx-auto mb-6 text-3xl text-slate-400 shadow-inner border border-slate-200"><i class="fa-solid fa-rocket"></i></div>
                        <h3 class="font-bold text-2xl text-slate-800 mb-1">PrintBet Studio</h3>
                        <p class="text-sm text-slate-500 mb-8 bg-slate-100 inline-block px-3 py-1 rounded-full font-mono" id="app-version-display">Version Loading...</p>
                        <button onclick="checkUpdate()" class="bg-slate-800 text-white px-8 py-3 rounded-full text-sm font-bold hover:bg-black transition shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"><i class="fa-solid fa-rotate mr-2"></i> 检查新版本</button>
                        <div id="update-status" class="mt-6 text-sm text-slate-500 min-h-[20px]"></div>
                    </div>
                </div>
                <div class="p-6 border-t bg-slate-50 flex justify-end gap-4">
                    <button onclick="closeSettings()" class="px-6 py-2.5 text-sm text-slate-500 font-bold hover:text-slate-800 hover:bg-slate-200 rounded-lg transition">取消</button>
                    <button onclick="saveConfig()" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2.5 rounded-lg font-bold text-sm shadow-lg shadow-blue-600/20 transition transform active:scale-95">保存配置</button>
                </div>
            </div>
        </div>
    </div>
    <div id="picker-modal" class="modal fixed inset-0 bg-slate-900/50 z-40 flex items-center justify-center backdrop-blur-sm"><div class="bg-white rounded-2xl shadow-2xl w-[650px] max-h-[85vh] flex flex-col"><div class="h-16 border-b px-6 flex items-center justify-between bg-slate-50"><div><h3 class="font-bold text-slate-800 text-lg" id="picker-title">选择</h3></div><button onclick="closePicker()" class="w-8 h-8 rounded-full bg-white border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-200 flex items-center justify-center transition"><i class="fa-solid fa-times"></i></button></div><div class="flex-1 p-8 overflow-y-auto bg-white" id="picker-content"></div><div class="p-5 border-t bg-slate-50 flex justify-end gap-3"><button onclick="closePicker()" class="px-6 py-2 rounded-lg font-bold text-slate-500 hover:bg-slate-200 transition">取消</button><button onclick="confirmPicker()" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2 rounded-lg font-bold shadow-lg shadow-blue-600/20 transition">确认选择</button></div></div></div>
    <div id="loading-mask" class="fixed inset-0 bg-white/90 z-[100] hidden flex-col items-center justify-center backdrop-blur-sm"><i class="fa-solid fa-circle-notch fa-spin text-5xl text-blue-600 mb-6"></i><div class="text-slate-600 font-bold text-lg animate-pulse" id="loading-text">Processing...</div></div>

    <script>
        let currentMode='football', tickets=[], activeRowIndex=-1, tempChoice='';
        const CONFIG = {
            football:{types:[{k:'SPF',v:'胜平负'},{k:'RQSPF',v:'让球'},{k:'CBF',v:'比分'},{k:'JQS',v:'总进球'},{k:'BQC',v:'半全场'}],defaults:{match:'周三001',type:'SPF',choice:'胜'}},
            basketball:{types:[{k:'SF',v:'胜负'},{k:'RFSF',v:'让分'},{k:'DXF',v:'大小分'},{k:'SFC',v:'胜分差'}],defaults:{match:'周三301',type:'SF',choice:'主胜'}},
            number:{types:[{k:'P3',v:'排列三'},{k:'P5',v:'排列五'},{k:'DLT',v:'大乐透'}],defaults:{match:'23125期',type:'P3',choice:'1,2,3'}}
        };

        // === Toast 通知系统 (核心升级) ===
        function showToast(msg, type='info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            let icon = type==='error'?'fa-circle-exclamation' : (type==='success'?'fa-check-circle':'fa-info-circle');
            let color = type==='error'?'text-red-500' : (type==='success'?'text-green-500':'text-blue-500');
            
            toast.innerHTML = `
                <i class="fa-solid ${icon} ${color} text-xl"></i>
                <div class="flex-1 text-sm font-medium text-slate-700">${msg}</div>
            `;
            
            container.appendChild(toast);
            // 自动消失
            setTimeout(() => {
                toast.style.animation = 'fadeOut 0.3s ease-in forwards';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // === 业务逻辑 ===
        function switchMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(`tab-${mode}`).classList.add('active');
            document.getElementById('passType').parentElement.style.visibility = mode === 'number' ? 'hidden' : 'visible';
            tickets = []; addNewRow();
        }
        function updateUI() {
            const container = document.getElementById('ticket-rows'); container.innerHTML='';
            tickets.forEach((t, idx) => {
                const opts = CONFIG[currentMode].types.map(o => `<option value="${o.k}" ${t.type===o.k?'selected':''}>${o.v}</option>`).join('');
                container.insertAdjacentHTML('beforeend', `<div class="grid grid-cols-12 gap-2 items-center bg-white p-2.5 rounded-xl border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition group"><div class="col-span-2"><input value="${t.match}" onchange="updTicket(${idx},'match',this.value)" class="w-full border rounded-lg px-3 py-1.5 text-sm font-mono font-bold text-slate-700 outline-none focus:border-blue-500 transition"></div><div class="col-span-2"><select onchange="updTicket(${idx},'type',this.value)" class="w-full border rounded-lg px-3 py-1.5 text-sm outline-none bg-white transition">${opts}</select></div><div class="col-span-7" onclick="openPicker(${idx})"><div class="w-full border bg-slate-50 rounded-lg px-4 py-1.5 text-sm cursor-pointer hover:bg-white hover:border-blue-500 text-blue-700 font-bold truncate flex justify-between items-center h-[34px] transition border-slate-200">${formatChoice(t.type,t.choice)} <i class="fa-solid fa-chevron-right text-[10px] text-slate-300 group-hover:text-blue-500"></i></div></div><div class="col-span-1 text-right"><button onclick="delRow(${idx})" class="w-8 h-8 rounded-full hover:bg-red-50 text-slate-300 hover:text-red-500 transition flex items-center justify-center"><i class="fa-solid fa-trash"></i></button></div></div>`);
            });
            document.getElementById('total-amount').innerText = tickets.length*2*document.getElementById('multiplier').value;
            refreshOMRPreview();
        }
        function formatChoice(type, val) { return val || '点击选择...'; }
        function updTicket(i, k, v) { tickets[i][k] = v; updateUI(); }
        function addNewRow() { tickets.push({...CONFIG[currentMode].defaults}); updateUI(); }
        function delRow(i) { tickets.splice(i, 1); updateUI(); }

        async function refreshOMRPreview() {
            const imgEl=document.getElementById('omr-preview-img'), ph=document.getElementById('omr-placeholder');
            if(tickets.length===0){imgEl.style.display='none';ph.style.display='flex';return;}
            try {
                const res = await fetch('/api/preview_omr', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({bets:tickets, passType:document.getElementById('passType').value, multiplier:document.getElementById('multiplier').value})});
                const d = await res.json();
                if(d.status==='ok' && d.img_base64){ imgEl.src="data:image/png;base64,"+d.img_base64; imgEl.style.display='block'; ph.style.display='none'; }
            } catch(e){}
        }

        async function doPrint() {
            if(tickets.length===0) return showToast("列表为空，无法出票", "error");
            showLoading(true, "正在生成 OMR 仿真指令...");
            try {
                const res = await fetch('/api/print', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({bets:tickets, passType:document.getElementById('passType').value, multiplier:document.getElementById('multiplier').value})});
                const d = await res.json();
                if(d.status==='ok') showToast("✅ 已发送至打印机", "success");
                else showToast("❌ " + d.msg, "error");
            } catch(e){ showToast("无法连接到打印服务", "error"); }
            finally { showLoading(false); }
        }

        async function startOCR() {
            let input = document.createElement('input'); input.type='file'; input.accept='image/*';
            input.onchange = async e => {
                if(!e.target.files[0]) return;
                showLoading(true, "AI 视觉识别中...");
                const fd = new FormData(); fd.append('image', e.target.files[0]);
                try {
                    const res = await fetch('/api/ocr', {method:'POST', body:fd});
                    const d = await res.json();
                    if(d.status==='ok') {
                        d.bets.forEach(b => tickets.push(b));
                        updateUI();
                        showToast(`成功识别 ${d.bets.length} 条投注`, "success");
                    } else {
                        // 语义化提示
                        if(d.msg.includes('HTTP')) showToast("请检查 Umi-OCR 是否开启了 HTTP 服务", "error");
                        else if(d.msg.includes('未提取')) showToast("未发现有效内容，请确保截图清晰", "error");
                        else showToast(d.msg, "error");
                    }
                } catch(err){ showToast("OCR 服务连接失败", "error"); }
                finally { showLoading(false); }
            };
            input.click();
        }

        // Settings & Utils
        function switchSettingsTab(t) { document.querySelectorAll('.settings-nav-item').forEach(e=>e.classList.remove('active')); document.querySelectorAll('.settings-panel').forEach(e=>e.classList.add('hidden')); document.getElementById(`nav-${t}`).classList.add('active'); document.getElementById(`panel-${t}`).classList.remove('hidden'); }
        async function openSettings() { document.getElementById('settings-modal').classList.remove('hidden'); try { const r=await fetch('/api/config/get'); const d=await r.json(); const sel=document.getElementById('cfg-printer'); sel.innerHTML=''; (d.printers||[]).forEach(p=>{const o=document.createElement('option');o.value=p;o.innerText=p;if(p===d.config.printer_name)o.selected=true;sel.appendChild(o);}); document.getElementById('cfg-ocr').value=d.config.ocr_url||''; document.getElementById('cfg-pass').value=d.config.default_pass_type||'2x1'; document.getElementById('cfg-multi').value=d.config.default_multiplier||10; document.getElementById('app-version-display').innerText=d.app_version; checkStatus(); } catch(e){ showToast("配置加载失败，使用默认值", "error"); } }
        function closeSettings() { document.getElementById('settings-modal').classList.add('hidden'); }
        async function saveConfig() { const c={printer_name:document.getElementById('cfg-printer').value,ocr_url:document.getElementById('cfg-ocr').value,default_pass_type:document.getElementById('cfg-pass').value,default_multiplier:document.getElementById('cfg-multi').value}; await fetch('/api/config/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)}); document.getElementById('passType').value=c.default_pass_type; document.getElementById('multiplier').value=c.default_multiplier; closeSettings(); checkStatus(); showToast("配置已保存", "success"); }
        
        function showLoading(s, t) { document.getElementById('loading-mask').style.display=s?'flex':'none'; document.getElementById('loading-text').innerText=t; }
        async function checkStatus() { try { const ocr=document.getElementById('cfg-ocr').value.includes('http'); const prn=!!document.getElementById('cfg-printer').value; document.getElementById('led-ocr').className=`w-2 h-2 rounded-full ${ocr?'bg-green-500 shadow-[0_0_8px_#22c55e]':'bg-red-500'}`; document.getElementById('led-prn').className=`w-2 h-2 rounded-full ${prn?'bg-green-500 shadow-[0_0_8px_#22c55e]':'bg-red-500'}`; } catch(e){} }
        
        async function testPrinter() { const p=document.getElementById('cfg-printer').value; if(!p) return showToast("请选择打印机", "error"); const r=await fetch('/api/test/printer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({printer:p})}); const d=await r.json(); d.status==='ok'?showToast("✅ 测试指令已发送","success"):showToast("❌ 连接失败","error"); }
        async function testOCR() { const u=document.getElementById('cfg-ocr').value; const r=await fetch('/api/test/ocr',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})}); const d=await r.json(); d.status==='ok'?showToast("✅ OCR 服务在线","success"):showToast("❌ OCR 连接失败","error"); }
        async function checkUpdate() { const msg=document.getElementById('update-status'); msg.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> 连接中...'; try{ const r=await fetch('/api/system/check_update'); const d=await r.json(); if(d.status==='ok'){ if(d.has_update) msg.innerHTML=`<span class="text-green-600 font-bold">新版本: ${d.latest_version}</span> <a href="#" onclick="openUrl('${d.download_url}')" class="underline text-blue-600 ml-2">下载</a>`; else msg.innerText="已经是最新版本"; } else msg.innerText="检查失败: "+d.msg; }catch(e){msg.innerText="网络错误";} }
        async function openUrl(u) { await fetch('/api/system/open_url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})}); }

        // Pickers
        function openPicker(idx) { activeRowIndex=idx; tempChoice=tickets[idx].choice; document.getElementById('picker-title').innerText=`${tickets[idx].match} - ${tickets[idx].type}`; document.getElementById('picker-content').innerHTML=''; if(tickets[idx].type==='CBF') renderScoreGrid(); else if(currentMode==='number') renderNumGrid(0,9); else if(['SPF','RQSPF','SF','RFSF','DXF'].includes(tickets[idx].type)) renderBasicGrid(tickets[idx].type); else renderInput(); document.getElementById('picker-modal').classList.add('open'); }
        function closePicker() { document.getElementById('picker-modal').classList.remove('open'); }
        function confirmPicker() { tickets[activeRowIndex].choice=tempChoice; updateUI(); closePicker(); }
        function renderBasicGrid(type) { const isBasket=['SF','RFSF','DXF'].includes(type); const opts=isBasket?[{v:'3',l:'主胜/大'},{v:'0',l:'主负/小'}]:[{v:'3',l:'胜'},{v:'1',l:'平'},{v:'0',l:'负'}]; if(type=='DXF'){opts[0].l='大(1)';opts[0].v='1';opts[1].l='小(2)';opts[1].v='2';} const d=document.createElement('div'); d.className='flex gap-6 justify-center pt-10'; opts.forEach(o=>{const b=document.createElement('div');b.className=`ball rect w-32 h-16 text-lg ${tempChoice==o.v?'active':''}`;b.innerText=o.l;b.onclick=()=>{tempChoice=o.v;document.querySelectorAll('.ball').forEach(x=>x.classList.remove('active'));b.classList.add('active');};d.appendChild(b);}); document.getElementById('picker-content').appendChild(d); }
        function renderScoreGrid() { const scores=['1:0','2:0','2:1','3:0','3:1','3:2','4:0','4:1','4:2','5:0','5:1','5:2','胜其他','0:0','1:1','2:2','3:3','平其他','0:1','0:2','1:2','0:3','1:3','2:3','0:4','1:4','2:4','0:5','1:5','2:5','负其他']; const d=document.createElement('div'); d.className='grid grid-cols-5 gap-4'; scores.forEach(s=>{const b=document.createElement('div');b.className=`ball rect w-full h-12 ${tempChoice==s?'active':''}`;b.innerText=s;b.onclick=()=>{tempChoice=s;document.querySelectorAll('.ball').forEach(x=>x.classList.remove('active'));b.classList.add('active');};d.appendChild(b);}); document.getElementById('picker-content').appendChild(d); }
        function renderNumGrid(min, max) { const d=document.createElement('div'); d.className='flex flex-wrap gap-4 justify-center'; let s=tempChoice.split(',').filter(x=>x); for(let i=min;i<=max;i++){const v=i.toString();const b=document.createElement('div');b.className=`ball ${s.includes(v)?'active':''}`;b.innerText=v;b.onclick=()=>{if(s.includes(v))s=s.filter(x=>x!==v);else s.push(v);tempChoice=s.join(',');b.classList.toggle('active');};d.appendChild(b);} document.getElementById('picker-content').appendChild(d); }
        function renderInput() { document.getElementById('picker-content').innerHTML=`<input class="w-full border p-4 rounded-xl text-xl outline-none focus:border-blue-500" value="${tempChoice}" oninput="tempChoice=this.value">`; }

        switchMode('football');
        window.onload = async () => { openSettings(); setTimeout(()=>closeSettings(), 100); };
    </script>
</body>
</html>
