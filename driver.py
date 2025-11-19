import datetime

class EscPosDriver:
    def generate_stream(self, lines, qr, pt, mu):
        c = []
        c.append(b'\x1B\x40\x1B\x61\x01\x1D\x21\x11' + "PrintBet Pro\n".encode('gbk') + b'\x1D\x21\x00')
        c.append(f"TIME: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n".encode('gbk'))
        c.append(b'--------------------------------\n\x1B\x61\x00')
        for l in lines: c.append((l+"\n").encode('gbk'))
        c.append(b'--------------------------------\n')
        c.append(f"PASS: {pt}   MULTI: {mu}\n".encode('gbk'))
        
        # 原生二维码指令
        c.append(b'\n\x1B\x61\x01Scan to Terminal:\n')
        qb = qr.encode('utf-8')
        l = len(qb) + 3
        pl, ph = l % 256, l // 256
        c.append(b'\x1D\x28\x6B\x03\x00\x31\x43\x06') # Size
        c.append(b'\x1D\x28\x6B' + bytes([pl, ph]) + b'\x31\x50\x30' + qb) # Store
        c.append(b'\x1D\x28\x6B\x03\x00\x31\x51\x30') # Print
        
        c.append(b'\n\n\n\x1D\x56\x00') # Cut
        return b''.join(c)

    def send_raw(self, name, data):
        try:
            import win32print
            p = win32print.OpenPrinter(name)
            try:
                win32print.StartDocPrinter(p, 1, ("PrintBet", None, "RAW"))
                win32print.StartPagePrinter(p)
                win32print.WritePrinter(p, data)
                win32print.EndPagePrinter(p)
                win32print.EndDocPrinter(p)
                return True
            finally: win32print.ClosePrinter(p)
        except: return False
