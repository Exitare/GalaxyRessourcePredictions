from pathlib import Path
import pandas as pd
from Services.FileSystem import Folder_Management, File_Management
import os
from Services.Configuration.Config import Config
from Services.Processing import PreProcessing
from time import sleep
import numpy as np
import logging
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import RandomForestRegressor
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

sns.set()


class File:
    def __init__(self, full_name: str, tool_folder: Path, raw_df=None):
        """
        the constructor for the class
        :param full_name:
        :param tool_folder:
        :param raw_df:
        """
        # Provides information whether the entity is a merged too file or a "real" file
        if raw_df is not None:
            self.merged_file = True
        else:
            self.merged_file = False

        if not self.merged_file:
            # Full path to the source file
            self.path = Path(Config.DATA_RAW_DIRECTORY, full_name)

        # Name of file with extension
        self.full_name = full_name

        if not self.merged_file:
            # Name of file without extension
            self.name = os.path.splitext(full_name)[0]
        else:
            self.name = full_name

        # List of labels present in the data set. The list is ideally a copy of the list specific in the config.ini
        # If a label is missing the data set it will not be present in here, and therefore not evaluated
        self.detected_labels = []
        self.verified = True

        # Check if its a merged file or not
        if self.merged_file:
            self.raw_df = raw_df
        else:
            # Load data set depending on memory saving modes
            if not Config.MEMORY_SAVING_MODE:
                self.raw_df = File_Management.read_file(self.full_name)
                if self.raw_df is None:
                    self.verified = False
                    return
            else:
                self.raw_df = pd.DataFrame()

        # Pre process the raw data set
        if not Config.MEMORY_SAVING_MODE:
            self.preprocessed_df = PreProcessing.pre_process_data_set(self.raw_df)
            self.detect_labels()
        else:
            self.preprocessed_df = pd.DataFrame()

        # Contains the test, train score, name of the file, and additional data for each file
        self.evaluation_results = dict()
        # Contains the test, train score, name of the file, and additional data for each file and each split
        self.split_evaluation_results = dict()
        # Contains y and y_hat values
        self.predicted_results = dict()
        # Contains the features importances for each file
        self.feature_importances = dict()
        # Contains the pca components with supporting functions for all labels
        self.pca_components = dict()
        # Contains all pca components as df for each label
        self.pca_components_data_frames = dict()

        # Prepare the internal data structure
        self.prepare_internal_data_structure()

        if not Config.MEMORY_SAVING_MODE:
            self.verify()

        # Return, because the file is not eligible to be evaluated.
        if not self.verified:
            return

        # The folder where all reports and plots are getting stored, only created if file is valid
        self.folder = Folder_Management.create_file_folder(tool_folder, self.name)

        if self.folder is not None:
            self.verified = True
        else:
            self.verified = False

        # Determines if a file is already evaluated or not
        self.evaluated = False

    def load_memory_sensitive_data(self):
        """
        Loads all the data and prepares data sets, which was skipped due to memory saving mode
        """
        self.__load_preprocess_raw_data()
        self.detect_labels()
        self.prepare_internal_data_structure()

    def prepare_internal_data_structure(self):
        """
        Prepares initial values for evaluation data
        """
        for label in self.detected_labels:
            self.evaluation_results[label] = pd.DataFrame(
                columns=['File Name', 'Train Score', 'Test Score', 'Potential Over Fitting', 'Initial Row Count',
                         'Initial Feature Count', 'Processed Row Count', 'Processed Feature Count'])
            self.predicted_results[label] = pd.DataFrame(columns=['y', 'y_hat'])

            self.feature_importances[label] = pd.DataFrame()
            self.pca_components[label] = None
            self.pca_components_data_frames[label] = pd.DataFrame()
            self.split_evaluation_results[label] = pd.DataFrame()

    # Loading and preprocessing
    def __load_preprocess_raw_data(self):
        """
        Loads the data set and preprocesses it
        Only used if memory saving mode is active
        :return:
        """
        if not self.merged_file:
            self.raw_df = File_Management.read_file(self.full_name)
            self.preprocessed_df = PreProcessing.pre_process_data_set(self.raw_df)
            return
        else:
            return

    def get_raw_df_statistics(self):
        """
        Returns column, row and feature count of the raw data set
        :return:
        """
        columns: int = len(self.raw_df.columns)
        rows: int = len(self.raw_df.index)
        features: int = columns - 1
        return columns, rows, features

    def detect_labels(self):
        """
        Detects if the labels specified in the config.ini are present for the preproccesed data set
        """
        for label in Config.LABELS:
            if label in self.preprocessed_df:
                self.detected_labels.append(label)

    def get_pre_processed_df_statistics(self):
        """
        Returns column, row and feature count of the raw data set
        :return:
        """
        columns: int = len(self.preprocessed_df.columns)
        rows: int = len(self.preprocessed_df.index)
        features: int = columns - 1
        return columns, rows, features

    def verify(self):
        """
        Check if the file passes all requirements to be able to be evaluated
        :return:
        """
        columns, rows, features = self.get_raw_df_statistics()
        if rows < Config.MINIMUM_ROW_COUNT:
            if Config.VERBOSE:
                logging.warning(f"{self.name} has insufficient rows ({rows}).")
                logging.warning("The file will not be evaluated.")
                sleep(1)
            self.verified = False

        if columns < Config.MINIMUM_COLUMN_COUNT:
            if Config.VERBOSE:
                logging.warning(f"{self.name} has insufficient columns ({columns}).")
                logging.warning("The file will not be evaluated.")
                sleep(1)
            self.verified = False

        # check for infinity values
        for column in self.preprocessed_df:
            if self.preprocessed_df[column].any() > np.iinfo('i').max:
                if Config.VERBOSE:
                    logging.warning(f"Detected infinity values in preprocessed data set!")
                    logging.warning(f"File will not be evaluated.")
                self.verified = False

        # Check if columns will pass variance selection
        for label in self.detected_labels:
            if label in self.preprocessed_df:
                check_df = self.preprocessed_df.copy()
                del check_df[label]
                check_df = PreProcessing.variance_selection(check_df)

                if 'numpy' not in str(type(check_df)):
                    self.verified = False

    # Prediction
    def predict(self, label: str):
        """
        Predicts the runtime for a complete data set.
        :return:
        """
        try:
            df = self.preprocessed_df.copy()

            model = RandomForestRegressor(n_estimators=Config.FOREST_ESTIMATORS, max_depth=Config.FOREST_MAX_DEPTH,
                                          random_state=1)

            y = df[label]
            del df[label]
            X = df

            source_row_count = len(X)

            X_indices = (X != 0).any(axis=1)
            X = X.loc[X_indices]
            y = y.loc[X_indices]

            if source_row_count != len(X) and Config.VERBOSE:
                logging.info(f"Removed {source_row_count - len(X)} row(s). Source had {source_row_count}.")

            X = PreProcessing.variance_selection(X)

            X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.8, random_state=1)

            model.fit(X_train, y_train)

            # Feature importance
            self.__calculate_feature_importance(label, model, df)

            y_test_hat = model.predict(X_test)
            y_train_hat = model.predict(X_train)
            train_score = r2_score(y_train, y_train_hat)
            test_score = r2_score(y_test, y_test_hat)

            over_fitting = False
            if train_score > test_score * 2:
                over_fitting = True

            self.evaluation_results[label] = self.evaluation_results[label].append(
                {'File Name': self.name, "Test Score": test_score,
                 "Train Score": train_score, "Potential Over Fitting": over_fitting,
                 "Initial Row Count": len(self.raw_df.index),
                 "Initial Feature Count": len(self.raw_df.columns) - 1, "Processed Row Count": len(X),
                 "Processed Feature Count": X.shape[1]}, ignore_index=True)
            self.predicted_results[label] = pd.concat(
                [pd.Series(y_test).reset_index()[label], pd.Series(y_test_hat)],
                axis=1)
            self.predicted_results[label].rename(columns={"runtime": "y", 0: "y_hat"}, inplace=True)

        except BaseException as ex:
            logging.exception(ex)

    def predict_partial(self, label: str):
        """
        Split the data into parts, and predicts results using only one part after another.
        """
        try:
            df = self.preprocessed_df.copy()

            model = RandomForestRegressor(n_estimators=Config.FOREST_ESTIMATORS, max_depth=Config.FOREST_MAX_DEPTH,
                                          random_state=1)

            # How many parts minimum. 3 is default.
            parts: int = 3
            if len(df) > 10000:
                while len(df) / parts > 3333:
                    parts += 1

            # how many rows should one part contain
            total_rows = int(len(df))
            parts_row_count: int = int(len(df) / parts)

            data_frames = []
            for part in range(parts):
                if part == 0:
                    data_frames.append(pd.DataFrame(df[:parts_row_count]))
                elif 0 < part < parts - 1:
                    data_frames.append(pd.DataFrame(df[(parts_row_count * part): (parts_row_count * (part + 1))]))
                else:
                    data_frames.append(pd.DataFrame(df[parts_row_count * part:]))

            for data_frame in data_frames:
                y = data_frame[label]
                del data_frame[label]
                X = data_frame

                source_row_count = int(len(X))
                source_feature_count = int(len(X.columns))
                X_indices = (X != 0).any(axis=1)
                X = X.loc[X_indices]
                y = y.loc[X_indices]

                X = PreProcessing.variance_selection(X)

                X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.8, random_state=1)

                model.fit(X_train, y_train)

                y_test_hat = model.predict(X_test)
                y_train_hat = model.predict(X_train)
                train_score = r2_score(y_train, y_train_hat)
                test_score = r2_score(y_test, y_test_hat)

                over_fitting = False
                if train_score > test_score * 2:
                    over_fitting = True

                self.split_evaluation_results[label] = self.split_evaluation_results[label].append(
                    {'File Name': self.name, "Test Score": test_score,
                     "Train Score": train_score, "Potential Over Fitting": over_fitting,
                     "Initial Row Count": source_row_count,
                     "Initial Feature Count": source_feature_count, "Processed Row Count": len(X),
                     "Processed Feature Count": X.shape[1], "Total rows": total_rows}, ignore_index=True)

            self.split_evaluation_results[label].sort_values(by='Test Score', ascending=False, inplace=True)

        except BaseException as ex:
            logging.exception(ex)

    def pca_analysis(self, label: str):
        """
        Generates a pca analysis
        """

        try:
            df = self.preprocessed_df.copy()

            y = df[label]
            del df[label]
            X = df
            X = PreProcessing.normalize_X(X)
            X = PreProcessing.variance_selection(X)

            self.pca_components[label] = PCA()
            X = self.pca_components[label].fit_transform(X)
            self.pca_components_data_frames[label] = pd.DataFrame(X)
            self.pca_components_data_frames[label][label] = pd.Series(y.values)

        except BaseException as ex:
            logging.exception(ex)

    # Reports
    def generate_reports(self):
        """
        Generate file specific reports
        :return:
        """

        # Report for evaluation results based on the whole data set
        for label, data in self.evaluation_results.items():
            if data.empty:
                continue

            data.to_csv(Path.joinpath(self.folder, f"{label}_evaluation_report.csv"), index=False)

        # Report for y and y_hat
        for label, data in self.predicted_results.items():
            if data.empty:
                continue

            data.to_csv(Path.joinpath(self.folder, f"{label}_predicted_values_report.csv"), index=False)

        # Report for the split evaluation
        for label, data in self.split_evaluation_results.items():
            if data.empty:
                continue
            data.to_csv(Path.joinpath(self.folder, f"{label}_split_evaluation_report.csv"), index=False)

        # Report for combined datasets (whole, splits)
        for label, data in self.__create_combined_evaluation_data_set().items():
            if data is None or data.empty:
                continue

            data.to_csv(Path.joinpath(self.folder, f"{label}_combined_evaluation_report.csv"), index=False)

    def __create_combined_evaluation_data_set(self) -> dict:
        """
        Creates a data set containing the full evaluation and the splits
        """
        compare_evaluations = dict()

        for label, data in self.split_evaluation_results.items():
            if data.empty:
                continue

            if label in compare_evaluations:
                data['split'] = True
                compare_evaluations[label] = compare_evaluations[label].append(data)
            else:
                compare_evaluations[label] = pd.DataFrame()
                data['split'] = True
                compare_evaluations[label] = compare_evaluations[label].append(data)

        for label, data in self.evaluation_results.items():
            if data.empty:
                continue

            if label in compare_evaluations:
                data['split'] = False
                compare_evaluations[label] = compare_evaluations[label].append(data)
            else:
                compare_evaluations[label] = pd.DataFrame()
                data['split'] = False
                compare_evaluations[label] = compare_evaluations[label].append(data)

        return compare_evaluations

    # Plots
    def generate_plots(self):
        """
        Helper to call all plotting functions
        :return:
        """
        self.__plot_predicted_values(True)
        self.__plot_predicted_values(False)
        self.__plot_feature_importance()
        self.__plot_feature_to_label_correlation()
        self.__plot_pca_analysis()
        self.__plot_pca_analysis_scatter()

    def __plot_predicted_values(self, log_scale: bool):
        """
        Plots the predicted values for the unmodified data set
        :return:
        """
        try:
            for label, data in self.predicted_results.items():
                if data.empty:
                    continue

                ax = sns.scatterplot(x='y', y='y_hat', label=label, data=data)

                if log_scale:
                    ax.set(xscale="log", yscale="log")

                if ax is None:
                    logging.warning("Could not plot predicted values, because axis where None")
                    return

                ax.legend()
                fig = ax.get_figure()
                if log_scale:
                    fig.savefig(os.path.join(self.folder, f"{label}_predicated_log_values.png"))
                else:
                    fig.savefig(os.path.join(self.folder, f"{label}_predicated_values.png"))
                fig.clf()
                plt.close('all')
        except BaseException as ex:
            logging.exception(ex)

    def __plot_feature_importance(self):
        """
        Plots the feature importance for each evaluation
        """

        for label, data in self.feature_importances.items():
            if data.empty:
                continue

            ax = sns.barplot(data=data)
            ax.set(xlabel='Feature', ylabel='Gini Index')
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
            ax.legend()
            fig = ax.get_figure()
            fig.savefig(os.path.join(self.folder, f"{label}_feature_importance.png"), bbox_inches='tight')
            fig.clf()
            plt.close('all')

    def __plot_feature_to_label_correlation(self):
        """
        Plots the correlation between the feature and labels
        """

        for label, data in self.feature_importances.items():
            if data.empty:
                continue

            important_features = []
            for col in data.columns:
                important_features.append(col)

            important_features.append(label)

            data = self.preprocessed_df[important_features]
            corr = data.corr()

            mask = np.triu(np.ones_like(corr, dtype=np.bool))
            f, ax = plt.subplots(figsize=(11, 9))
            cmap = sns.diverging_palette(220, 10, as_cmap=True)
            sns.heatmap(corr, mask=mask, cmap=cmap, vmax=.3, center=0,
                        square=True, linewidths=.5, cbar_kws={"shrink": .5})

            fig = ax.get_figure()
            fig.savefig(os.path.join(self.folder, f"{label}_correlation_matrix.png"), bbox_inches='tight')
            fig.clf()

    def __plot_pca_analysis(self):
        """
        Plots all features and their weight
        """
        try:
            for label, data in self.pca_components.items():
                if data is None:
                    continue

                features = range(data.n_components_)
                plt.bar(features, data.explained_variance_ratio_, color='black')
                plt.xlabel('PCA features')
                plt.ylabel('variance %')
                plt.xticks(features)
                plt.xticks(rotation=90, fontsize=8)
                plt.tight_layout()
                plt.savefig(Path.joinpath(self.folder, f"{label}_pca_features.png"), bbox_inches='tight')
                plt.clf()
                plt.close('all')

        except BaseException as ex:
            logging.exception(ex)
            return

    def __plot_pca_analysis_scatter(self):
        """
        Plots the clustering of the first most important pca components
        """

        try:
            for label, data in self.pca_components_data_frames.items():
                if data.empty:
                    continue

                temp_data = data.copy()
                temp_data[label] = np.log(temp_data[label])

                ax = sns.scatterplot(x=data[0], y=data[1],
                                     hue=label,
                                     data=temp_data)
                ax.set(xlabel='Component 1', ylabel='Component 2')
                ax.legend()
                fig = ax.get_figure()
                fig.savefig(Path(self.folder, f"{label}_pca_cluster.png"), bbox_inches='tight')
                fig.clf()
                plt.close('all')
        except BaseException as ex:
            logging.exception(ex)
            input()

    def __calculate_feature_importance(self, label: str, model, df):
        """
        Calculates the feature importance for the given model
        """
        feats = {}  # a dict to hold feature_name: feature_importance
        for feature, importance in zip(df.columns, model.feature_importances_):
            feats[feature] = importance  # add the name/value pair

        importance = pd.DataFrame.from_dict(feats, orient='index').rename(columns={0: 'Gini-importance'})
        importance.sort_values(by='Gini-importance', inplace=True, ascending=False)

        importance_indices = importance[importance['Gini-importance'].gt(0.01)].index

        self.feature_importances[label] = importance.T[importance_indices]

    # Cleanup
    def free_memory(self):
        """
        Release not required memory for memory saving mode.
        :return:
        """
        if not Config.MEMORY_SAVING_MODE:
            return

        self.raw_df = None
        self.preprocessed_df = None
