from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import Lasso, RidgeCV
from sklearn.ensemble import RandomForestRegressor
from Services.PreProcessing import normalize_X
import Constants


# Negative crossvalidation score
# https://stackoverflow.com/questions/21443865/scikit-learn-cross-validation-negative-values-with-mean-squared-error

# Why splitting twice
# https://datascience.stackexchange.com/questions/15135/train-test-validation-set-splitting-in-sklearn


def predict_cpu_usage(df):
    """
    Trains the model to predict the cpu usage
    This function will be deprected in further version and is therefore not maintained anymore.
    As galaxy is only setting the cpu count by a handwritten algorithm this is not useful to predict.
    :param df:
    :return:
    """
    print("CPU usage prediction started...")

    # Prepare dataframe
    y = df['processor_count']
    del df['processor_count']
    X = df
    X = normalize_X(X)
    print("Training model...")

    model = select_model()
    X_train, X_test, y_train, y_test, X_val, y_val = splitting_model(X, y)
    model.fit(X_train, y_train)
    y_test_hat = model.predict(X_test)

    print(f"CPU model test score is : {model.score(X_test, y_test)}")
    print(f"CPU model train score is : {model.score(X_train, y_train)}")
    # print(f"Prediction: {y_test_hat[:5]}")

    scores = cross_val_score(model, X, y, cv=5)
    print(f"CPU Cross validation score is : {scores}")
    print("")


def predict_memory_usage(df):
    """
    Trains the model to predict memory usage
    :param df:
    :return:
    """

    # Prepare dataframe
    y = df['memtotal']
    del df['memtotal']
    X = df
    X = normalize_X(X)

    # Select model
    model = select_model()

    # Split and train model
    X_train, X_test, y_train, y_test, X_val, y_val = splitting_model(X, y)
    model.fit(X_train, y_train)
    y_test_hat = model.predict(X_test)

    # Calculate model score
    print(f"Memory model test score is : {model.score(X_test, y_test)}")
    print(f"Memory model train score is : {model.score(X_train, y_train)}")
    # print(f"Prediction: {y_test_hat}")

    # Calculate cross validation
    scores = cross_val_score(model, X, y, cv=5)
    print(f"Memory Cross validation score is : {scores}")
    return model, model.score(X_test, y_test), model.score(X_train, y_train), cross_val_score(model, X, y, cv=5)


def predict_total_time(df):
    """
    Trains the model to predict the total time
    :param df:
    :return:
    """

    # Prepare dataframe
    y = df['runtime']
    del df['runtime']
    X = df
    X = normalize_X(X)

    # Select model
    model = select_model()

    # Split and train model
    X_train, X_test, y_train, y_test, X_val, y_val = splitting_model(X, y)
    model.fit(X_train, y_train)
    y_test_hat = model.predict(X_test)

    # Calculate model scores
    print(f"Total time model test score is : {model.score(X_test, y_test)}")
    print(f"Total time model train score is : {model.score(X_train, y_train)}")
    # print(f"Prediction: {y_test_hat}")

    # Calculate cross validation
    scores = cross_val_score(model, X, y, cv=5)
    print(f"Total time Cross validation score is : {scores}")
    return model, model.score(X_test, y_test), model.score(X_train, y_train), cross_val_score(model, X, y, cv=5)


def splitting_model(X, y):
    """
    Using the train_test_split function twice, to generate a valid train, test and validation set.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=1)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.33, random_state=1)
    return X_train, X_test, y_train, y_test, X_val, y_val


def select_model():
    """
    Select the appropriate model based on the given argument
    """
    if Constants.SELECTED_ALGORITHM == Constants.Model.RIDGE.name:
        return RidgeCV(alphas=[0.1, 1.0, 10.0])

    elif Constants.SELECTED_ALGORITHM == Constants.Model.LASSO.name:
        return Lasso()

    else:
        return RandomForestRegressor(n_estimators=12, random_state=0)