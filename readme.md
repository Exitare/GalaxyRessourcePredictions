# Galaxy Resource Predictions


## Overview

This tool is able to predict different parts of a dataset generated by galaxy jobs.

- CPU count
- Memory Usage
- Total time (job duration)

To get a prediction, the data provided needs to be preprocessed. 
The tool is using scikit`s StandardScaler which is used a z-score apporach.  
Additionally columns which are not useful for predictions like job name or job id are removed from the dataset before normalization.  
Predictions are based on Linear Regression. One has the chance to use plain linear regression, Ridge or Lasso.  
This can be specified with a cli argument.

After prediction, scores are calculated. More precisely the model.score and the cross validation score.  
Also the weights of features (coefficents) are printed.   
The coefficents are listed in order of the columns there are assigned to.
So the first weight is the first column which is used for prediction.

## Installation

These packages are required for using this tool.

- [scikit-learn](https://scikit-learn.org/stable/install.html) 
- [argparse](https://docs.python.org/3/library/argparse.html)
- [pandas](https://pandas.pydata.org)


## Command Line Arguments

Right now two command line arguments are available.
- filename (required)
- model (optional)

Filename is required because the filename must be given. There is no default value.  
Model is optional. The model specifies the machine learning algorithm used for training the model.  
If no model is specified, plain Linear Regression is used. Other possibilities are Lasso or Ridge.

## Sample Data

Sampla data is provided for bwa-mem algorithm and stringtie.    
Please have a look at the Data/ folder.


## Example usage

Plain Linear regression:
```python RessourcePredictor.py --filename Data/bwa_mem_0.7.15.1_example.csv ``` 

Using Lasso:
```python RessourcePredictor.py --filename Data/bwa_mem_0.7.15.1_example.csv --model=LASSO``` 
