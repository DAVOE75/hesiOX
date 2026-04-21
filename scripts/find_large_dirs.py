import os

def get_size(start_path='.'):
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass
    except:
        pass
    return total_size

result = []
for d in os.listdir('/opt/hesiox'):
    fp = os.path.join('/opt/hesiox', d)
    if os.path.isdir(fp):
        size_mb = get_size(fp) / (1024 * 1024)
        result.append((d, size_mb))

result.sort(key=lambda x: x[1], reverse=True)

for name, size in result:
    print(f"{name}: {size:.2f} MB")
