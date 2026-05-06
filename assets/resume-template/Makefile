# Makefile for daily-job-hunter resume template
# Targets: pdf (LaTeX), typst (Typst), clean

.PHONY: pdf typst clean

pdf:
	pdflatex -interaction=nonstopmode resume.tex
	pdflatex -interaction=nonstopmode resume.tex

typst:
	typst compile resume.typ resume.pdf

clean:
	rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk resume.pdf
