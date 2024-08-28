#!/bin/bash

ORIGIN_BRANCH=$1
cd /mountedpath/
# Figure out the differences between this commit and the origin / master branch
echo "INFO: Finding the list of files that changed compared to the origin branch '${ORIGIN_BRANCH}'"
FILES_CHANGED="`git diff --name-only --diff-filter=ACMRU $ORIGIN_BRANCH`"
if [[ $? -ne 0 ]]
then
    echo "ERROR: Something went wrong getting the list of files that changed compared to the origin branch"
    exit 1
fi

# Filter out the .py files and run the checks on them
PYTHON_FILES_TO_CHECK=`echo "$FILES_CHANGED" | grep '.py$'`
if [[ "$PYTHON_FILES_TO_CHECK" == "" ]]
then
    echo "INFO: No .py files changed in the git commit, not running any code quality checks"
    exit 0
fi

printf "INFO: .py files that changed, and those that will be checked are: $PYTHON_FILES_TO_CHECK \n \n"

printf "################ INFO: Running pylint #################### \n"
time pylint -j 0 $PYTHON_FILES_TO_CHECK
PYLINT_EXIT_CODE=${PIPESTATUS[0]}
PYLINT_RESULT="PASSED"
if [[ $PYLINT_EXIT_CODE -ne 0 ]]
then
      PYLINT_RESULT="FAILED"
fi

printf "\n \n############### INFO: Running pycodestyle ################ \n"
time pycodestyle --ignore=E501,W504 $PYTHON_FILES_TO_CHECK
PYCODESTYLE_EXIT_CODE=${PIPESTATUS[0]}
PYCODESTYLE_RESULT="PASSED"
if [[ $PYCODESTYLE_EXIT_CODE -ne 0 ]]
then
      PYCODESTYLE_RESULT="FAILED"
fi

printf "\n \n################# INFO: Running pep257 ################### \n"
time pep257 $PYTHON_FILES_TO_CHECK --explain --source --count
PEP257_EXIT_CODE=${PIPESTATUS[0]}
PEP257_RESULT="PASSED"
if [[ $PEP257_EXIT_CODE -ne 0 ]]
then
      PEP257_RESULT="FAILED"
fi

printf "\n \n---- Code Style Check Results Summary ---- \n"
echo "pylint:                       ${PYLINT_RESULT}"
echo "pycodestyle:                  ${PYCODESTYLE_RESULT}"
echo "pep257:                       ${PEP257_RESULT}"
echo "------------------------------------------"
if [[ $PYLINT_EXIT_CODE -ne 0 ]] || [[ $PYCODESTYLE_EXIT_CODE -ne 0 ]] || [[ $PEP257_EXIT_CODE -ne 0 ]]
then
    echo "ERROR: code style checks failed, see above for details. Please fix and commit again"
    exit 1
fi
