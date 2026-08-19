# Running this on Windows

Written for a locked-down machine: no administrator rights, no WSL, no software
centre. Everything below installs into your own user profile.

## The short version

Three things are needed: Python, the Tesseract OCR engine, and OCRmyPDF. None of
them requires administrator rights if you install them this way.

```powershell
# 1. Miniforge — a per-user conda. Download the Windows x86_64 installer from
#    https://conda-forge.org/download/  and run it. When asked, choose
#    "Just Me". It installs to %USERPROFILE%\miniforge3 and touches nothing else.

# 2. The OCR engine, from the same source this pipeline was built against.
conda create -y -n ocr -c conda-forge tesseract

# 3. OCRmyPDF and the spreadsheet library, into that environment.
conda activate ocr
pip install ocrmypdf openpyxl
```

Then confirm:

```powershell
ocrmypdf --version
tesseract --list-langs        # eng and fra must both appear
```

**Ghostscript is not needed.** OCRmyPDF used to require it, and most guides on the
internet still say so. It can rasterize with pypdfium2 instead, which arrives as a
pip wheel with no installer. Pass `--rasterizer pypdfium` and `--output-type pdf`
and Ghostscript never enters the picture. This was tested by removing Ghostscript
from `PATH` entirely and re-running a seven-page authorization: the OCR text came
out character-for-character identical to the Ghostscript run, same length, same
content, on every page.

That matters because Ghostscript is the one dependency here with no automated
installer and no per-user story. Skipping it removes the only step that would have
needed a help-desk ticket.

## Running it

```powershell
conda activate ocr
cd D:\work\release-folder

$env:TEMP = "D:\ocr_tmp"
mkdir $env:TEMP -Force

ocrmypdf --language eng+fra --output-type pdf --rasterizer pypdfium `
         --skip-text --rotate-pages --optimize 0 --jobs 8 `
         --sidecar RELEASE_OCR.txt RELEASE.pdf RELEASE_OCR.pdf

python pipeline\segment.py RELEASE_OCR.txt segs.json
python pipeline\build_new.py RELEASE_OCR.txt segs.json out.xlsx RELEASE.pdf
```

The backtick is PowerShell's line continuation, where a Linux shell uses a
backslash. `--jobs` takes a number; `$env:NUMBER_OF_PROCESSORS` uses every core,
and leaving two free keeps the machine usable during a long run.

## If Miniforge itself is blocked

Some policies block installers by publisher regardless of install location. Two
fallbacks, in order of preference:

1. **Python from the Microsoft Store**, which installs per-user and is often
   allowed where downloaded installers are not. Then `pip install --user ocrmypdf
   openpyxl`. You still need the Tesseract binary — see below.
2. **Tesseract from the Appveyor CI build artifacts.** The Tesseract project
   documents these as standalone binaries built with Visual Studio, distributed as
   an archive rather than an installer. Extract to a folder you own, then point at
   it for the session:

   ```powershell
   $env:PATH = "D:\tools\tesseract;$env:PATH"
   $env:TESSDATA_PREFIX = "D:\tools\tesseract\tessdata"
   ```

If Tesseract will not run at all, the pipeline cannot proceed — the scripts read
OCR text and do not produce it. That is the point to ask for help, and the ask is
small and specific: one binary, no service, no system change.

## Language data

The conda-forge Tesseract package ships a large set of language files. On the Linux
machine this pipeline was built on it carried 125 of them, French included.

Verify rather than assume:

```powershell
tesseract --list-langs
```

If `fra` is missing, download `fra.traineddata` from the tessdata repository into
the `tessdata` folder shown by `tesseract --print-parameters`, or set
`TESSDATA_PREFIX` to a folder containing it.

**Do not skip this if the package contains any French.** A French document read
with English-only OCR does not error. It produces text that matches nothing, the
document becomes invisible to the segmenter, and nothing in the output says a
document is missing.

## Traps specific to Windows

**Temp space.** OCR writes rendered images and intermediates per page. A
1,842-page package at 400 dpi produced about 2.7 GB of temporary files. `%TEMP%`
defaults to `C:`, which on a managed machine is often the smallest volume. Point it
somewhere with room before starting, not after a job dies halfway.

**Paths longer than 260 characters.** Release filenames are long and sync folders
nest deeply. Work from a short root such as `D:\work\`.

**Spaces in filenames.** Real packages carry names like
`A-2021-00215_CBL - Release Package.pdf`. Quote every path.

**Cloud sync.** Running OCR inside a synced folder makes the sync client upload
every intermediate as it appears. Work locally, move the results in afterwards.

**Line endings.** The scripts read and write UTF-8 explicitly and split pages on
form feeds, so they behave the same on either platform.

## Doing it with Copilot or another assistant

Useful for the mechanical parts, unreliable in one specific place. Split it.

**Worth delegating:** translating commands between bash and PowerShell, adapting
paths, reading a stack trace, widening a regex for a form wording the scripts do
not yet handle, writing a throwaway script to check a result.

**Check yourself, every time:**

- **Install instructions.** Assistants confidently produce `apt install` for
  Windows, and they will almost certainly tell you to install Ghostscript, because
  every guide written before it became optional says so. It is not needed.
- **Language flags.** `--language eng+fra` is correct. `--lang`, `--languages` and
  `--language en+fr` are not. Confirm the code against `tesseract --list-langs`.
- **Any number it reports.** If it says the extraction found 47 authorizations, ask
  which pages, then open two of them.

**The rule that decides everything:** every value this pipeline writes carries the
page it came from, so ask for the page and look. An assistant told to "fill in the
missing habitat areas" will fill them in, and the numbers will look reasonable.
Automatic extraction of those figures agreed with known-good values 76% of the time,
which is why the pipeline queues them for a person instead of writing them. Pointed
at that queue, an assistant is genuinely useful. Allowed to write the cells, it
produces a spreadsheet nobody can defend.

**A prompt that works:**

> I have a scanned Access to Information release package as a PDF and this pipeline
> in `pipeline/`. Read `README.md` and `CLAUDE.md` first. OCR the PDF with every
> language present in it, run the segmenter, then tell me how many documents it
> found and how that compares to the number of pages containing an "issued to"
> block. Do not build the workbook until those two numbers are close.

That last sentence is the method. A segmenter that finds 10 documents where 19
exist produces a clean, confident, badly incomplete spreadsheet, and nothing about
the output announces the problem.
