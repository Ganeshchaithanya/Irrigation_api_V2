import struct
import os

def get_video_info(file_path):
    print(f"File: {os.path.basename(file_path)}")
    print(f"Size: {os.path.getsize(file_path)} bytes")
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Simple search for track header (tkhd) atom
    idx = 0
    tracks = []
    while True:
        idx = data.find(b'tkhd', idx)
        if idx == -1:
            break
        
        # tkhd version & flags
        # size is 4 bytes before 'tkhd'
        try:
            size = struct.unpack('>I', data[idx-4:idx])[0]
            version = data[idx+4]
            if version == 0:
                # Width and height are at the very end of tkhd (which has size 92 bytes)
                # tkhd layout:
                # 4 bytes size
                # 4 bytes type
                # 1 byte version
                # 3 bytes flags
                # 4 bytes creation_time
                # 4 bytes modification_time
                # 4 bytes track_id
                # 4 bytes reserved
                # 4 bytes duration
                # 8 bytes reserved
                # 2 bytes layer
                # 2 bytes alternate_group
                # 2 bytes volume
                # 2 bytes reserved
                # 36 bytes matrix
                # 4 bytes width (fixed point 16.16)
                # 4 bytes height (fixed point 16.16)
                width_offset = idx + 80
                height_offset = idx + 84
                w_fp = struct.unpack('>I', data[width_offset:width_offset+4])[0]
                h_fp = struct.unpack('>I', data[height_offset:height_offset+4])[0]
                width = w_fp >> 16
                height = h_fp >> 16
                if width > 0 and height > 0:
                    tracks.append((width, height))
            elif version == 1:
                # Width and height are at the end of version 1 tkhd (size 104 bytes)
                # Let's read it if needed
                width_offset = idx + 92
                height_offset = idx + 96
                w_fp = struct.unpack('>I', data[width_offset:width_offset+4])[0]
                h_fp = struct.unpack('>I', data[height_offset:height_offset+4])[0]
                width = w_fp >> 16
                height = h_fp >> 16
                if width > 0 and height > 0:
                    tracks.append((width, height))
        except Exception as e:
            print(f"  Error parsing track at index {idx}: {e}")
        idx += 4
        
    for w, h in tracks:
        print(f"  Track Dimensions: {w}x{h} (Aspect Ratio: {w/h:.3f} or ~{w}:{h})")
    print("-" * 40)

if __name__ == '__main__':
    get_video_info('Aquasol_Splash_Screen.mp4')
    get_video_info('Aquasol_Splash_Screen_2.mp4')
    if os.path.exists('aquasol_app/assets/images/aquasol_splash.mp4'):
        get_video_info('aquasol_app/assets/images/aquasol_splash.mp4')
