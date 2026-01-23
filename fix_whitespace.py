file_path = r"d:\Official\AssetIQ_Production_Batch-9\apps\hq_backend\routers\dashboard.py"

with open(file_path, encoding="utf-8") as f:
    lines = f.readlines()

# Remove trailing whitespace from each line
cleaned_lines = [line.rstrip() + "\n" for line in lines]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(cleaned_lines)

print(f"Cleaned whitespace in {file_path}")
