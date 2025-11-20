# -*- coding: utf-8 -*-
import datetime
import sys

class EscPosDriver:
    def get_printers(self):
        """获取系统所有打印机列表"""
        try:
            import win32print
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            return [p[2] for p in printers]
        except Exception as e:
            return ["XP-58"]

    def build_escpos(self, ticket_data, qr_data, pt, mu):
        """生成 OMR 仿真打印指令"""
        cmds = []
        
        # 指令集
        CMD_INIT = b'\x1B\x40'
        CMD_CENTER = b'\x1B\x61\x01'
        CMD_LEFT = b'\x1B\x61\x00'
        CMD_BOLD_ON = b'\x1B\x45\x01'
        CMD_BOLD_OFF = b'\x1B\x45\x00'
        CMD_REV_ON = b'\x1D\x42\x01' 
        CMD_REV_OFF = b'\x1D\x42\x00'
        CMD_SMALL = b'\x1B\x4D\x01'
        CMD_NORMAL = b'\x1B\x4D\x00'

        # 1. 票头
        cmds.append(CMD_INIT)
        cmds.append(CMD_CENTER)
        cmds.append(b'\x1D\x21\x10') # 倍高
        # 容错: 如果 ticket_data 里没有 title，用默认的
        title = ticket_data.get('title', 'PrintBet Ticket')
        cmds.append(title.encode('gbk') + b'\n')
        cmds.append(b'\x1D\x21\x00') # 恢复
        
        cmds.append(b'--------------------------------\n')
        cmds.append(CMD_LEFT)
        
        human_data = ticket_data.get('human_readable', [])
        
        for item in human_data:
            # 场次行
            cmds.append(CMD_BOLD_ON)
            cmds.append(f"{item['match']}".encode('gbk'))
            cmds.append(CMD_BOLD_OFF)
            cmds.append(b'\n')
            
            # OMR 区域
            omr_rows = item['omr_rows']
            is_sfc = len(omr_rows) > 1
            if is_sfc: cmds.append(CMD_SMALL)
            
            for row in omr_rows:
                cmds.append(b' ')
                item_count = 0
                for opt in row:
                    if item_count > 5 and not is_sfc:
                         cmds.append(b'\n ')
                         item_count = 0
                    
                    if opt['active']:
                        cmds.append(CMD_REV_ON + CMD_BOLD_ON + opt['text'].encode('gbk') + CMD_BOLD_OFF + CMD_REV_OFF)
                    else:
                        cmds.append(opt['text'].encode('gbk'))
                    
                    cmds.append(b' ')
                    item_count += 1
                cmds.append(b'\n')
            
            if is_sfc: cmds.append(CMD_NORMAL)
            cmds.append(b'\n')

        cmds.append(b'--------------------------------\n')
        cmds.append(CMD_CENTER)
        cmds.append(f"Pass: {pt}   Multi: {mu}\n".encode('gbk'))
        cmds.append(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n".encode('gbk'))
        
        # QR Code
        cmds.append(b'\nScan to Terminal:\n')
        qb = qr_data.encode('utf-8')
        l = len(qb) + 3
        pl, ph = l % 256, l // 256
        cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x43\x08')
        cmds.append(b'\x1D\x28\x6B' + bytes([pl, ph]) + b'\x31\x50\x30' + qb)
        cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x51\x30')
        
        cmds.append(b'\n\n\n\x1D\x56\x00')
        return b''.join(cmds)

    def send_raw(self, printer_name, data):
        try:
            import win32print
            p = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(p, 1, ("PrintBet Job", None, "RAW"))
                win32print.StartPagePrinter(p)
                win32print.WritePrinter(p, data)
                win32print.EndPagePrinter(p)
                win32print.EndDocPrinter(p)
                return True
            finally:
                win32print.ClosePrinter(p)
        except Exception as e:
            print(f"Printer Error: {e}")
            return False
