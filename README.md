# UIO recomended prerequisites

This is a repo for finding the links between uio courses.
It eventually plots a dot for each course in a circle, and links them to their recomended prerequisites.
The plot is interactive, hover over points will highligt courses needed to take it, and courses requiering it. You can also click each course to get the course page.

Feel free to play around with, tough be careful. Everything is quite slow, and this likely wont ever be fixed.
The code is written over the course of 24h, never revised, and an effor was made for norwegian variable names, though no effort was put into variable names in general.
This is to say, it works, and thats about it! No documentation, no well-written code, no great performance, and a few known bugs.

Enjoy!

## How to use

One commandline argument is needed. It is the code for the faculty or institute you want to get the courses of. For instance, if you want all Science sourses, write `matnat`. For a specific institute, the facult is also required, as such `matnat/fys`, for all courses managed by Institute of Physics. `alle/uio` is also a valid commandline argument, and will gather all 3876 courses offered by the University of Oslo. Good luck plotting that :)


