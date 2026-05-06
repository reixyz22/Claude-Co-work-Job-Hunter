% resume.cls — daily-job-hunter sidebar resume class
% Generic single-page sidebar layout. Customize via \mysidestyle / \mysidewidth / \mysidecolor.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{resume}[2026/05/06 daily-job-hunter sidebar resume]

\LoadClass[10pt,letterpaper]{article}

\RequirePackage[margin=0.5in]{geometry}
\RequirePackage{xcolor}
\RequirePackage{paracol}
\RequirePackage{titlesec}
\RequirePackage{enumitem}
\RequirePackage[hidelinks]{hyperref}

% === Customization hooks ===
% Override any of these in resume.tex to restyle without touching the class.
\providecommand{\mysidestyle}{}                  % runs at top of sidebar column (e.g., add a banner)
\providecommand{\mysidewidth}{0.32}              % sidebar width as fraction of page (0.25 - 0.40 typical)
\providecommand{\mysidecolor}{black!75!white}    % accent color for section headers

% === Section style ===
\titleformat{\section}{\large\bfseries\color{\mysidecolor}}{}{0em}{}[\vspace{-2pt}\titlerule]
\titlespacing*{\section}{0pt}{6pt}{4pt}

% === Tight list defaults for bullets ===
\setlist[itemize]{leftmargin=*,itemsep=2pt,topsep=2pt,parsep=0pt}

% === No page numbers (single-page resume) ===
\pagenumbering{gobble}

% === Convenience commands ===
\newcommand{\name}[1]{{\Huge\bfseries #1}\par\vspace{4pt}}
\newcommand{\role}[2]{\textbf{#1}\hfill{\small\itshape #2}\par}

% === Two-column layout: sidebar left, main right ===
\newcommand{\beginresume}{%
  \mysidestyle
  \columnratio{\mysidewidth}%
  \begin{paracol}{2}%
}
\newcommand{\endresume}{\end{paracol}}

\endinput
