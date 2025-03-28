"""
THIS CODE IS ENTIRELY DEEPSEEK GENERATED, so please note that some features are not avaible
Oh, and also, i did not tested auth
"""

import websockets
import asyncio
import struct
from collections import defaultdict
import traceback

SE_COLORS = [
    "#6D001A", "#BE0039", "#FF4500", "#FFA800", "#FFD635",
    "#FFF8B8", "#00A368", "#00CC78", "#7EED56", "#00756F",
    "#009EAA", "#00CCC0", "#2450A4", "#3690EA", "#51E9F4",
    "#493AC1", "#6A5CFF", "#94B3FF", "#811E9F", "#B44AC0",
    "#E4ABFF", "#DE107F", "#FF3881", "#FF99AA", "#6D482F",
    "#9C6926", "#000000", "#898D90", "#D4D7D9", "#FFFFFF"
]

class TextwallClient:
    def __init__(self):
        self.ws = None
        self.grid = defaultdict(dict)
        self.cursors = defaultdict(dict)
        self.wall_bounds = None
        self.user_id = None

    async def connect(self):
        self.ws = await websockets.connect(
            "wss://tw.2s4.me/ws",
            extra_headers={
                "User-Agent": "PythonTextWall/1.0",
                "Origin": "https://tw.2s4.me"
            }
        )
        await self.send_join("", "")

    async def send(self, data):
        await self.ws.send(data)

    async def send_join(self, wall, subwall):
        join_msg = self.serialize({"j": [wall, subwall]})
        await self.send(join_msg)
    def _parse_number(self, val):
        """Convert various number formats to integer"""
        if isinstance(val, str):
            if val.startswith('<0x'):
                return int(val[3:-1], 16)
            try:
                return int(val)
            except ValueError:
                return 0
        return int(val) if isinstance(val, (int, float)) else 0
    def serialize(self, obj):
        if isinstance(obj, dict):
            msg = bytearray()
            msg.append(0x80 + len(obj))
            for k, v in obj.items():
                msg.extend(self.serialize(k))
                msg.extend(self.serialize(v))
            return bytes(msg)
        elif isinstance(obj, list):
            msg = bytearray()
            msg.append(0x90 + len(obj))
            for item in obj:
                msg.extend(self.serialize(item))
            return bytes(msg)
        elif isinstance(obj, str):
            encoded = obj.encode()
            return bytes([0xA0 + len(encoded)]) + encoded
        elif isinstance(obj, int):
            if 0 <= obj <= 127:
                return bytes([obj])
            else:
                return struct.pack(">i", obj)
        elif isinstance(obj, bytes):
            return bytes([0xC4, len(obj)]) + obj
        else:
            raise ValueError(f"Unserializable type: {type(obj)}")

    async def receive_loop(self):
        try:
            async for message in self.ws:
                try:
                    parsed = self.parse_message(message)
                    self.handle_message(parsed)
                except Exception as e:
                    print(f"Error: {e}\nRaw: {message.hex()}")
        except websockets.ConnectionClosed:
            print("Connection closed")

    def parse_message(self, data):
        ptr = 0
        result = []
        while ptr < len(data):
            obj, ptr = self._parse_value(data, ptr)
            result.append(obj)
        return result[0] if len(result) == 1 else result

    def _parse_value(self, data, ptr):
        if ptr >= len(data):
            return None, ptr
            
        header = data[ptr]
        ptr += 1
        
        # Fixstr
        if 0xA0 <= header <= 0xBF:
            length = header - 0xA0
            if ptr + length > len(data):
                return f"<truncated str@{ptr}>", len(data)
            try:
                return data[ptr:ptr+length].decode(), ptr+length
            except UnicodeDecodeError:
                return data[ptr:ptr+length], ptr+length
        
        # Fixmap
        if 0x80 <= header <= 0x8F:
            return self._parse_map(data, ptr, header - 0x80)
        
        # Fixarray
        if 0x90 <= header <= 0x9F:
            return self._parse_array(data, ptr, header - 0x90)
        
        # Signed integers
        if header == 0xD2:  # int32
            if ptr + 4 > len(data):
                return "<truncated int32>", len(data)
            return struct.unpack(">i", data[ptr:ptr+4])[0], ptr+4
        if header == 0xD3:  # int64
            if ptr + 8 > len(data):
                return "<truncated int64>", len(data)
            return struct.unpack(">q", data[ptr:ptr+8])[0], ptr+8
        
        # Binary
        if header == 0xC4:
            if ptr + 1 > len(data):
                return "<truncated bin8>", len(data)
            length = data[ptr]
            ptr += 1
            if ptr + length > len(data):
                return f"<truncated bin {length}>", len(data)
            return data[ptr:ptr+length], ptr+length
        
        # Special cases
        if header == 0xC2: return False, ptr
        if header == 0xC3: return True, ptr
        if header == 0x00: return "", ptr  # Empty string key
        
        return f"<0x{header:02x}>", ptr

    def _parse_map(self, data, ptr, length):
        result = {}
        for _ in range(length):
            if ptr >= len(data):
                return result, ptr
            key, ptr = self._parse_value(data, ptr)
            if ptr >= len(data):
                return result, ptr
            val, ptr = self._parse_value(data, ptr)
            result[key] = val
        return result, ptr

    def _parse_array(self, data, ptr, length):
        result = []
        for _ in range(length):
            if ptr >= len(data):
                return result, ptr
            val, ptr = self._parse_value(data, ptr)
            result.append(val)
        return result, ptr
    def handle_complex_text_update(self, msg):
        """Handle nested text updates like [{'e': {'e': [...]}}, ...]"""
        try:
            # Extract the nested data structure
            data = msg[0]['e']['e']
            coords = []
            char_data = []
            
            # Parse hex strings to integers
            for item in msg[1:]:
                if isinstance(item, str) and item.startswith('<0x'):
                    char_data.append(int(item[3:-1], 16))
                elif isinstance(item, int):
                    char_data.append(item)
            
            # First 4 bytes are coordinates (x, y)
            if len(char_data) >= 4:
                x = (char_data[0] << 8) | char_data[1]
                y = (char_data[2] << 8) | char_data[3]
                self.process_chunk(x, y, bytes(char_data[4:]))
        except Exception as e:
            traceback.print_exception(e)
            print(f"Failed to parse complex text update: {e}")

    def process_chunk(self, base_x, base_y, data):
        """Enhanced chunk processor with better error handling"""
        try:
            print(f"✏️ Chunk at ({base_x},{base_y}) [{len(data)} bytes]")
            for i in range(0, len(data), 2):
                if i+1 >= len(data):
                    break

                char_code = data[i]
                color_byte = data[i+1]
                
                # Calculate cell position
                cell_x = base_x + (i//2 % 20)
                cell_y = base_y + (i//2 // 20)
                
                # Decode character and colors
                char = chr(char_code) if char_code < 0x10FFFF else '�'
                fg = color_byte % 31
                bg = color_byte // 31
                
                # Store in grid
                self.grid[(cell_x, cell_y)] = {
                    'char': char,
                    'fg': SE_COLORS[fg],
                    'bg': SE_COLORS[bg]
                }
                
                print(f"  ({cell_x:3},{cell_y:3}): {char} | "
                    f"FG: {SE_COLORS[fg]:9} | BG: {SE_COLORS[bg]}")
        except Exception as e:
            print(f"Error processing chunk: {e}")
    def handle_message(self, msg):
        if isinstance(msg, list):
            if len(msg) >= 2 and isinstance(msg[0], dict) and 'cu' in msg[0]:
                self.handle_cursor_update(msg)
            elif isinstance(msg[0], dict) and 'e' in msg[0]:
                self.handle_complex_text_update(msg)
            else:
                print("📦 List message:", msg)
        elif isinstance(msg, dict):
            if 'online' in msg:
                print(f"👥 Online: {msg['online']}")
            elif 'j' in msg:
                print(f"🚪 Joined: {'/'.join(msg['j'])}")
            elif 'cu' in msg:
                self.handle_cursor_update([msg, ""])
            elif 'b' in msg:
                self.handle_bounds(msg['b'])
            elif 'e' in msg:
                self.handle_text_update(msg['e'])
            elif 'rc' in msg:  # Add this case
                self.handle_remove_cursor(msg['rc'])
            else:
                print("📨 Unknown dict:", msg)
        else:
            print("📦 Raw:", msg)

    def handle_cursor_update(self, msg):
        """Handle complex cursor formats with hex keys"""
        try:
            # Extract cursor data from nested structure
            cursor_data = msg[0]['cu']
            raw_values = msg[1:]
            
            # Convert hex strings to proper values
            converted = {}
            for k, v in cursor_data.items():
                if isinstance(k, str) and k.startswith('<0x'):
                    key = int(k[3:-1], 16)
                    converted[key] = self._parse_hex_value(v)
                else:
                    converted[k] = v

            # Get coordinates with fallback
            x = self._parse_number(converted.get(0x6c, [0, 0])[0])  # 0x6c = 'l' key
            y = self._parse_number(converted.get(0x6c, [0, 0])[1])
            
            # Extract username from trailing elements
            username = next((item for item in raw_values 
                            if isinstance(item, str) and len(item) > 1), "anonymous")

            # Get color (0x63 = 'c' key)
            color = converted.get(0x63, 0) % len(SE_COLORS)

            # Update cursor tracking
            cursor_id = converted.get('id', 'unknown')
            self.cursors[cursor_id] = {
                'pos': (x, y),
                'name': username,
                'color': SE_COLORS[color]
            }
            print(f"🖱️ {username} moved to ({x}, {y}) with color {SE_COLORS[color]}")

        except Exception as e:
            print(f"Cursor parse error: {e}")

    def _parse_hex_value(self, val):
        """Convert hex string values to numbers"""
        if isinstance(val, str) and val.startswith('<0x'):
            return int(val[3:-1], 16)
        return val

    def parse_number(self, val):
        if isinstance(val, str) and val.startswith("<0x"):
            return int(val[3:-1], 16)
        return int(val) if isinstance(val, (int, float)) else 0

    def handle_bounds(self, bounds):
        if isinstance(bounds, list) and len(bounds) >= 4:
            self.wall_bounds = bounds
            print(f"🗺️ Bounds: {bounds}")
        else:
            print("⚠️ Invalid bounds")
    def handle_remove_cursor(self, user_id):
        """Remove a cursor from tracking"""
        if user_id in self.cursors:
            name = self.cursors[user_id].get('name', 'unknown')
            del self.cursors[user_id]
            print(f"🚪 {name} left the wall")
        else:
            print(f"ℹ️ Unknown user left: {user_id}")
    def handle_text_update(self, data):
        if isinstance(data, dict):
            if 'a' in data and 'chunks' in data:
                x, y = data['a']
                self.process_chunk(x*20, y*10, data['chunks'])
        elif isinstance(data, bytes) and len(data) >= 8:
            x = struct.unpack(">i", data[0:4])[0]
            y = struct.unpack(">i", data[4:8])[0]
            self.process_chunk(x, y, data[8:])
        else:
            print("🔠 Unknown text format")

    def process_chunk(self, base_x, base_y, data):
        print(f"✏️ Chunk at ({base_x},{base_y}) [{len(data)} bytes]")
        for i in range(0, len(data), 2):
            if i+1 >= len(data):
                break
            char_code = data[i]
            color_byte = data[i+1]
            fg, bg = color_byte % 31, color_byte // 31
            x = base_x + (i//2 % 20)
            y = base_y + (i//2 // 20)
            char = chr(char_code) if char_code < 0x10FFFF else "�"
            self.grid[(x, y)] = (char, SE_COLORS[fg], SE_COLORS[bg])

async def main():
    client = TextwallClient()
    await client.connect()
    
    async def keep_alive():
        while True:
            await asyncio.sleep(30)
            await client.send(b"\x80")  # Empty map
    
    asyncio.create_task(keep_alive())
    
    try:
        await client.receive_loop()
    except KeyboardInterrupt:
        print("Disconnecting...")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())