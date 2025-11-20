# -*- coding: utf-8 -*-
import datetime
import sys
from PIL import Image

class EscPosDriver:
    def get_printers(self):
        """获取系统所有打印机列表"""
        try:
            import win32print
            # 枚举本地和网络打印机
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            return [p[2] for p in printers]
        except Exception as e:
            print(f"Enum Printers Error: {e}")
            # 返回一个默认值防止前端下拉框为空
            return ["XP-58", "Microsoft Print to PDF"]

    def image_to_commands(self, img):
        """
        【核心功能】将 PIL Image 对象转为 ESC/POS 光栅位图指令 (GS v 0)
        用于打印 OMR 引擎生成的仿真答题卡图片
        """
        try:
            # 1. 调整尺寸适配 80mm 热敏纸 (标准宽度约 576 dots)
            # 如果图片过宽，按比例缩放；如果正好或较小，保持原样
            target_w = 576
            if img.width > target_w:
                ratio = target_w / img.width
                new_h = int(img.height * ratio)
                img = img.resize((target_w, new_h), Image.Resampling.LANCZOS)
            
            # 2. 二值化处理 (确保只有黑白两色)
            img = img.convert('1')
            
            # 3. 构建指令
            w, h = img.size
            x_bytes = (w + 7) // 8  # 每行需要的字节数
            
            # GS v 0 m xL xH yL yH d1...dk
            # m=0 (Normal mode)
            cmd = b'\x1D\x76\x30\x00'
            cmd += x_bytes.to_bytes(2, 'little') # 宽度 (字节数)
            cmd += h.to_bytes(2, 'little')       # 高度 (点数)
            
            # 4. 像素位反转
            # PIL 中: 0=黑, 1=白
            # ESC/POS 中: 1=打印(黑), 0=不打(白)
            # 因此需要将 bits 反转
            pixels = img.tobytes()
            # 使用 bytearray 和异或操作进行反转
            inverted = bytearray([b ^ 0xFF for b in pixels])
            
            # 5. 拼接指令 + 切纸
            return cmd + inverted + b'\n\n\n\x1D\x56\x00'
            
        except Exception as e:
            print(f"Image Conversion Error: {e}")
            return b''

    def build_escpos(self, ticket_data, qr_data, pt, mu):
        """
        【兼容模式】生成基于文本的 OMR 仿真指令 (反白字符模式)
        用于 logic.py 生成的结构化数据打印
        """
        cmds = []
        
        # ESC/POS 常用指令
        CMD_INIT = b'\x1B\x40'
        CMD_CENTER = b'\x1B\x61\x01'
        CMD_LEFT = b'\x1B\x61\x00'
        CMD_BOLD_ON = b'\x1B\x45\x01'
        CMD_BOLD_OFF = b'\x1B\x45\x00'
        CMD_REV_ON = b'\x1D\x42\x01'  # 反白开启 (黑底白字)
        CMD_REV_OFF = b'\x1D\x42\x00' # 反白关闭
        CMD_SMALL = b'\x1B\x4D\x01'   # 压缩字体
        CMD_NORMAL = b'\x1B\x4D\x00'  # 正常字体

        # 1. 票头
        cmds.append(CMD_INIT)
        cmds.append(CMD_CENTER)
        cmds.append(b'\x1D\x21\x10') # 倍高
        title = ticket_data.get('title', 'PrintBet Ticket')
        cmds.append(title.encode('gbk') + b'\n')
        cmds.append(b'\x1D\x21\x00') # 恢复正常大小
        
        cmds.append(b'--------------------------------\n')
        cmds.append(CMD_LEFT)
        
        human_data = ticket_data.get('human_readable', [])
        
        for item in human_data:
            # 场次行 (加粗)
            cmds.append(CMD_BOLD_ON)
            cmds.append(f"{item['match']}".encode('gbk'))
            cmds.append(CMD_BOLD_OFF)
            cmds.append(b'\n')
            
            # 选项区域
            omr_rows = item.get('omr_rows', [])
            # 如果是胜分差(SFC)等多行内容，使用压缩字体防止换行
            is_sfc = len(omr_rows) > 1
            if is_sfc: cmds.append(CMD_SMALL)
            
            for row in omr_rows:
                cmds.append(b' ')
                item_count = 0
                for opt in row:
                    # 简单的自动换行保护 (防止一行超过纸宽)
                    if item_count > 5 and not is_sfc:
                         cmds.append(b'\n ')
                         item_count = 0
                    
                    if opt['active']:
                        # 选中项：反白 + 加粗
                        cmds.append(CMD_REV_ON + CMD_BOLD_ON + opt['text'].encode('gbk') + CMD_BOLD_OFF + CMD_REV_OFF)
                    else:
                        # 未选中项：普通文本
                        cmds.append(opt['text'].encode('gbk'))
                    
                    cmds.append(b' ')
                    item_count += 1
                cmds.append(b'\n')
            
            if is_sfc: cmds.append(CMD_NORMAL)
            cmds.append(b'\n')

        # 页脚
        cmds.append(b'--------------------------------\n')
        cmds.append(CMD_CENTER)
        cmds.append(f"Pass: {pt}   Multi: {mu}\n".encode('gbk'))
        cmds.append(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n".encode('gbk'))
        
        # 打印二维码 (用于终端机识别)
        cmds.append(b'\nScan to Terminal:\n')
        if qr_data:
            qb = qr_data.encode('utf-8')
            l = len(qb) + 3
            pl, ph = l % 256, l // 256
            # ESC/POS 二维码指令 (Store & Print)
            cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x43\x08') # 模块大小 8
            cmds.append(b'\x1D\x28\x6B' + bytes([pl, ph]) + b'\x31\x50\x30' + qb)
            cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x51\x30')
        
        # 切纸
        cmds.append(b'\n\n\n\x1D\x56\x00')
        return b''.join(cmds)

    def send_raw(self, printer_name, data):
        """发送二进制数据到 Windows 打印机"""
        if not data:
            return False
            
        try:
            import win32print
            p = win32print.OpenPrinter(printer_name)
            try:
                # 开启打印作业
                job = win32print.StartDocPrinter(p, 1, ("PrintBet Job", None, "RAW"))
                win32print.StartPagePrinter(p)
                win32print.WritePrinter(p, data)
                win32print.EndPagePrinter(p)
                win32print.EndDocPrinter(p)
                return True
            finally:
                win32print.ClosePrinter(p)
        except Exception as e:
            print(f"[Driver Error] Send raw failed: {e}")
            return False
