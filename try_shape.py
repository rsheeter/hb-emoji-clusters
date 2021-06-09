from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib.tables._g_l_y_f import Glyph
from pathlib import Path
import re
import requests
import subprocess

def download_text(url, dest):
	if dest.is_file():
		return
	response = requests.get(url)
	response.raise_for_status()
	with open(dest, "w") as f:
		f.write(response.text)
	print(url, "=>", dest)

def sequences(unicode_file):
	seqs = set()
	with open(unicode_file) as f:
		for line in f:
			if "#" in line:
				line = line[:line.index("#")]
			if ";" in line:
				line = line[:line.index(";")]
			line = line.strip()
			if not line:
				continue
			seqs.add(tuple(int(v, 16) for v in line.split(" ")))
	return seqs

hb_shape_file = Path(__file__).parent / "harfbuzz" / "build" / "util" / "hb-shape"
assert hb_shape_file.is_file(), f"Missing {hb_shape_file}"

emoji_test_file = Path(__file__).parent / "emoji-test.txt"
download_text("https://unicode.org/Public/emoji/14.0/emoji-test.txt", emoji_test_file)
rgis = sequences(emoji_test_file)

not_a_real_font = Path(__file__).parent / "not-a-font.ttf"
with open(not_a_real_font, "w") as f:
	f.write("meh")

print(f"Testing {len(rgis)} sequences against {not_a_real_font}...")

good = set()
bad = set()
for rgi in rgis:
	rgi_str = ",".join(f"U+{cp:04x}" for cp in rgi)
	cmd = [
		str(hb_shape_file),
		f"--font-file={str(not_a_real_font)}",
		f"--unicodes={rgi_str}",
		"--no-positions"
	]

	result = subprocess.run(cmd, capture_output=True, text=True)
	assert result.returncode == 0, result

	stdout = result.stdout.strip()
	assert stdout.startswith("[") and stdout.endswith("]"), result
	stdout = stdout[1:-1]
	clusters = {int(v.split("=")[1]) for v in stdout.split("|")}
	if len(clusters) == 1:
		good.add(rgi)
	else:
		print(rgi_str, "bad_cluster", stdout)
		bad.add(rgi)

print(f"{len(bad)} / {len(good) + len(bad)} failures")
