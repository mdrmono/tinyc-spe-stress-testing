Welcome to the SPE-TinyCC project!

This project is a tool for testing the correctness of the TinyCC compiler.

It was created as part of CMPT 479: Special Topics in Computing Systems at
Simon Fraser University.

Authors:
- Rashed Hadi (rmh7)
- Kavi Godden (kgodden)
- Manuel Delfin(mda99)

# Running the project
- Step 1: Build the docker image
```
 > docker build -t spe-tinycc .
 > docker run -it --rm -v $(pwd):/spe spe-tinycc
```
- Step 2: Place any files you want to enumerate and test in the input directory
- Step 3: Create the variants of the files in the input directory
```
 > python3 -m src.spe input/ output/
```
 - this till load all the vairiants for each test in input into a folder in output
- Step 4: Test the TinyCC compiler on the variants
```
 > python3 -m src.diff_testing --log testing_summary.txt output/
```
 - this will put the info for each test result into a testing_summary.txt file
 - you can find a sumarry of the test results at the bottom of the 
   testing_summary. txt file.
   
   
