import os
import threading
from flask import Flask, request, render_template_string
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.request

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
WEB_URL = os.environ.get('WEB_URL', '') 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghép Ảnh FC Mobile</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: Arial, sans-serif; background-color: var(--tg-theme-bg-color, #f4f4f9); color: var(--tg-theme-text-color, #000); padding: 15px; margin: 0; }
        .container { background: var(--tg-theme-secondary-bg-color, #fff); padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #2196F3; margin-top: 5px;}
        label { font-weight: bold; display: block; margin-top: 15px; margin-bottom: 5px; font-size: 14px;}
        input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 14px; margin-top: 20px; background-color: var(--tg-theme-button-color, #2196F3); color: var(--tg-theme-button-text-color, #fff); border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:active { opacity: 0.8; }
        .loading { display: none; text-align: center; margin-top: 15px; color: #ff9800; font-weight: bold;}
        
        /* Khu vực hiển thị ảnh và kéo thả */
        #previewArea { display: none; position: relative; width: 100%; border: 2px dashed #bbb; border-radius: 8px; margin-top: 15px; overflow: hidden; background: #eee;}
        #imageStack img { width: 100%; display: block; pointer-events: none; /* Khong cho cham vao anh de tranh loi keo web */ }
        .drag-text { position: absolute; background-color: #0092fa; color: white; padding: 6px 10px; border-radius: 6px; font-weight: bold; font-size: 12px; cursor: grab; user-select: none; touch-action: none; box-shadow: 0 2px 5px rgba(0,0,0,0.4); z-index: 10; white-space: nowrap;}
        .drag-text:active { cursor: grabbing; }
        .guide-text { font-size: 12px; color: #e91e63; font-style: italic; display: none; margin-top: 5px; font-weight: bold;}
    </style>
</head>
<body>
    <div class="container">
        <h2>TOOL GHÉP ẢNH</h2>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="hidden" id="chat_id" name="chat_id">
            
            <label>1. Chọn các ảnh để ghép:</label>
            <input type="file" id="images" name="images" accept="image/*" multiple required>
            
            <label>2. Chữ góc trên (VD: Ms1377):</label>
            <input type="text" id="text1" name="text1" placeholder="Bỏ trống nếu không chèn">
            
            <label>3. Chữ góc dưới (VD: Login...):</label>
            <input type="text" id="text2" name="text2" placeholder="Bỏ trống nếu không chèn">
            
            <div id="guideText" class="guide-text">👇 Bạn hãy DÙNG TAY KÉO THẢ các ô chữ màu xanh trên ảnh dưới đây để chọn vị trí ưng ý nhất nhé!</div>
            
            <!-- Khu vực Preview cho Mobile -->
            <div id="previewArea">
                <div id="imageStack"></div>
                <div id="wm1" class="drag-text" style="display:none; top: 10%; left: 5%;"></div>
                <div id="wm2" class="drag-text" style="display:none; top: 80%; left: 5%;"></div>
            </div>
            
            <button type="submit" id="submitBtn">✅ TIẾN HÀNH GHÉP ẢNH</button>
            <div id="loading" class="loading">⏳ Đang xử lý và gửi ảnh HD về Chat... Vui lòng đợi!</div>
        </form>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            document.getElementById('chat_id').value = tg.initDataUnsafe.user.id;
        } else { document.getElementById('chat_id').value = "0"; }

        // Logic hiển thị chữ lên Preview
        const txt1 = document.getElementById('text1');
        const txt2 = document.getElementById('text2');
        const wm1 = document.getElementById('wm1');
        const wm2 = document.getElementById('wm2');
        const guideText = document.getElementById('guideText');

        function updateWm() {
            let hasText = false;
            if(txt1.value.trim()){ wm1.innerText = txt1.value; wm1.style.display = 'inline-block'; hasText = true;} else { wm1.style.display = 'none'; }
            if(txt2.value.trim()){ wm2.innerText = txt2.value; wm2.style.display = 'inline-block'; hasText = true;} else { wm2.style.display = 'none'; }
            
            if(hasText && document.getElementById('images').files.length > 0) {
                guideText.style.display = 'block';
            } else {
                guideText.style.display = 'none';
            }
        }
        txt1.addEventListener('input', updateWm);
        txt2.addEventListener('input', updateWm);

        // Logic tải ảnh Preview
        document.getElementById('images').addEventListener('change', function(e){
            const files = e.target.files;
            const stack = document.getElementById('imageStack');
            stack.innerHTML = '';
            if(files.length > 0){
                document.getElementById('previewArea').style.display = 'block';
                for(let f of files){
                    let img = document.createElement('img');
                    img.src = URL.createObjectURL(f);
                    stack.appendChild(img);
                }
                updateWm();
            } else {
                document.getElementById('previewArea').style.display = 'none';
                guideText.style.display = 'none';
            }
        });

        // Logic Kéo Thả bằng cảm ứng (Touch)
        function makeDrag(el) {
            let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            el.ontouchstart = dragStart;
            el.onmousedown = dragStart;

            function dragStart(e) {
                e.preventDefault();
                let ev = e.type.includes('touch') ? e.touches[0] : e;
                pos3 = ev.clientX;
                pos4 = ev.clientY;
                document.ontouchend = dragEnd;
                document.ontouchmove = dragMove;
                document.onmouseup = dragEnd;
                document.onmousemove = dragMove;
            }
            function dragMove(e) {
                e.preventDefault(); // Chặn cuộn trang web khi đang kéo chữ
                let ev = e.type.includes('touch') ? e.touches[0] : e;
                pos1 = pos3 - ev.clientX;
                pos2 = pos4 - ev.clientY;
                pos3 = ev.clientX;
                pos4 = ev.clientY;
                
                let parent = el.parentElement;
                let newTop = el.offsetTop - pos2;
                let newLeft = el.offsetLeft - pos1;
                
                // Giữ chữ không bị kéo lọt ra ngoài khung ảnh
                if(newTop < 0) newTop = 0;
                if(newLeft < 0) newLeft = 0;
                if(newTop + el.offsetHeight > parent.offsetHeight) newTop = parent.offsetHeight - el.offsetHeight;
                if(newLeft + el.offsetWidth > parent.offsetWidth) newLeft = parent.offsetWidth - el.offsetWidth;
                
                el.style.top = newTop + "px";
                el.style.left = newLeft + "px";
            }
            function dragEnd() {
                document.ontouchend = null; document.ontouchmove = null;
                document.onmouseup = null; document.onmousemove = null;
            }
        }
        makeDrag(wm1); makeDrag(wm2);

        // Nút Gửi lên Server
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if(document.getElementById('images').files.length < 2) {
                tg.showAlert("Vui lòng chọn ít nhất 2 ảnh!"); return;
            }
            
            document.getElementById('submitBtn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            let formData = new FormData(this);

            // Tính toán phần trăm (Tọa độ) của chữ trên điện thoại để gửi lên máy chủ
            let parent = document.getElementById('previewArea');
            let x1_pct = wm1.offsetLeft / parent.offsetWidth;
            let y1_pct = wm1.offsetTop / parent.offsetHeight;
            let x2_pct = wm2.offsetLeft / parent.offsetWidth;
            let y2_pct = wm2.offsetTop / parent.offsetHeight;

            formData.append('x1', x1_pct);
            formData.append('y1', y1_pct);
            formData.append('x2', x2_pct);
            formData.append('y2', y2_pct);

            fetch('/api/process', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    tg.showAlert("✅ Thành công! Hãy đóng cửa sổ này và kiểm tra tin nhắn Bot.");
                    tg.close();
                } else {
                    tg.showAlert("❌ Lỗi: " + data.message);
                    document.getElementById('submitBtn').style.display = 'block';
                    document.getElementById('loading').style.display = 'none';
                }
            }).catch(error => {
                tg.showAlert("❌ Lỗi kết nối!");
                document.getElementById('submitBtn').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def mini_app_home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_images():
    try:
        chat_id = request.form.get('chat_id')
        text1 = request.form.get('text1', '').strip()
        text2 = request.form.get('text2', '').strip()
        
        # Nhận tọa độ kéo thả từ điện thoại
        x1_pct = float(request.form.get('x1', 0.05))
        y1_pct = float(request.form.get('y1', 0.1))
        x2_pct = float(request.form.get('x2', 0.05))
        y2_pct = float(request.form.get('y2', 0.8))
        
        files = request.files.getlist('images')

        if len(files) < 2: return {"success": False, "message": "Cần ít nhất 2 ảnh"}

        cac_anh = [Image.open(f.stream).convert("RGB") for f in files]
        chieu_rong, chieu_cao = zip(*(anh.size for anh in cac_anh))
        
        max_rong = max(chieu_rong)
        tong_cao = sum(chieu_cao)
        
        anh_moi = Image.new('RGB', (max_rong, tong_cao), color=(0,0,0))
        toa_do_y = 0
        for anh in cac_anh:
            anh_moi.paste(anh, (0, toa_do_y))
            toa_do_y += anh.size[1]

        def tao_anh_chu(text, max_rong):
            if not text: return None
            
            font_size = int(max_rong * 0.055)
            font_path = "Roboto-Bold.ttf"
            
            if not os.path.exists(font_path):
                try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", font_path)
                except: pass
                    
            try: font = ImageFont.truetype(font_path, font_size)
            except: font = ImageFont.load_default()
            
            temp_img = Image.new("RGBA", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            padding_x, padding_y = int(font_size * 0.8), int(font_size * 0.5)
            wm_w = (bbox[2] - bbox[0]) + padding_x * 2
            wm_h = (bbox[3] - bbox[1]) + padding_y * 2
            wm_img = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(wm_img)
            draw.rounded_rectangle([0, 0, wm_w, wm_h], radius=int(font_size * 0.4), fill="#0092fa")
            draw.text((padding_x, padding_y - int(font_size * 0.1)), text, fill="white", font=font)
            return wm_img

        wm1 = tao_anh_chu(text1, max_rong)
        wm2 = tao_anh_chu(text2, max_rong)

        # Chèn chữ vào vị trí đã được tính toán từ thao tác kéo thả trên đt
        if wm1: anh_moi.paste(wm1, (int(max_rong * x1_pct), int(tong_cao * y1_pct)), mask=wm1)
        if wm2: anh_moi.paste(wm2, (int(max_rong * x2_pct), int(tong_cao * y2_pct)), mask=wm2)

        img_byte_arr = io.BytesIO()
        anh_moi.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)

        if chat_id and chat_id != "0": bot.send_photo(chat_id, img_byte_arr, caption="✅ Ảnh của bạn đã ghép xong!")
        return {"success": True, "message": "Hoàn tất"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🎨 Mở Tool Ghép Ảnh", web_app=WebAppInfo(url=WEB_URL))
    markup.add(btn)
    bot.send_message(message.chat.id, "Chào mừng bạn đến với Bot Ghép Ảnh FC Mobile!\n\nHãy nhấn vào nút bên dưới để mở Mini App nhé.", reply_markup=markup)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
