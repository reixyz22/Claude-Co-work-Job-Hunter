// resume.typ — daily-job-hunter resume in Typst (fallback when pdflatex isn't installed)
// Customize sidebar-width and sidebar-color below.

#let sidebar-width = 32%
#let sidebar-color = rgb("#333333")

// === Layout primitives ===
#set page(margin: 0.5in, paper: "us-letter", numbering: none)
#set text(size: 10pt)
#set par(leading: 0.55em)

#let section-title(t) = {
  v(6pt)
  text(weight: "bold", size: 12pt, fill: sidebar-color, t)
  v(-3pt)
  line(length: 100%, stroke: 0.5pt + sidebar-color)
  v(2pt)
}

#let role(title, when) = {
  grid(
    columns: (1fr, auto),
    align: (left, right),
    text(weight: "bold", title),
    text(style: "italic", size: 9pt, when),
  )
}

// === Two-column layout ===
#grid(
  columns: (sidebar-width, 1fr),
  column-gutter: 18pt,

  // === Sidebar ===
  [
    #text(size: 24pt, weight: "bold")[Your Name]

    #section-title("Contact")
    your.email\@example.com \
    +1 555 555 5555 \
    City, State \
    #link("https://linkedin.com/in/your-handle")[linkedin.com/in/your-handle] \
    #link("https://github.com/your-handle")[github.com/your-handle]

    #section-title("Skills")
    *Languages:* Python, JavaScript \
    *Frameworks:* React, Flask \
    *Tools:* Git, Docker, AWS

    #section-title("Education")
    *Your University* \
    B.S. in Computer Science, 20XX
  ],

  // === Main ===
  [
    #section-title("Projects")
    #role("Project Name", "Tech stack")
    - Concrete bullet with a real metric.
    - Another concrete bullet.

    #section-title("Experience")
    #role("Job Title — Company", "Start – End")
    - Concrete accomplishment with a real metric.
    - Another concrete accomplishment.

    #section-title("Teaching / Leadership")
    #role("Role", "Org, dates")
    - One concrete line.
  ]
)
