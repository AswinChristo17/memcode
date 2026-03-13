import subprocess, sys, os
 
result = subprocess.run(
    [sys.executable, "-c", "import site; print(site.getusersitepackages())"],
    capture_output=True, text=True
)
site_packages = result.stdout.strip()
pth_file = os.path.join(site_packages, "memcode.pth")
 
project_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(site_packages, exist_ok=True)
 
with open(pth_file, "w") as f:
    f.write(project_dir + "\n")
 
print(f"✓ Written: {pth_file}")
print(f"  Points to: {project_dir}")
print("\nNow try: memcode --help")