import pandas as pd
from Entities.File import File
from RuntimeContants import Runtime_Folders
from Services.FileSystem import Folder_Management
from Services.Configuration.Config import Config
from pathlib import Path
import logging
from time import sleep
import os
import seaborn as sns
import shutil
import matplotlib.pyplot as plt
from Services.Helper import Data_Frame_Helper
import numpy as np


class Tool:
    def __init__(self, name: str):
        self.name = name
        self.combined_data_set = pd.DataFrame()
        # Timestamped folder for this specific run of the application.
        self.evaluation_dir = Runtime_Folders.EVALUATION_DIRECTORY
        # the tool folder
        self.folder = Folder_Management.create_tool_folder(self.name)
        self.all_files = []
        # All files not eligible to be checked
        self.excluded_files = []
        # All files eligible to be evaluated
        self.verified_files = []

        self.statistics = pd.DataFrame(columns=["Data", "Label", "Mean", "Median", "Correlation"])
        # Evaluation results overview for all evaluated labels
        self.files_label_overview = pd.DataFrame()

        # if all checks out, the tool will be flag as verified
        # Tools flagged as not verified will not be evaluated
        if self.folder is not None:
            self.verified = True
        else:
            self.verified = False

    def __eq__(self, other):
        """
        Checks if another tool entity is equal to this one
        :param other:
        :return:
        """
        return self.name == other.name

    def add_file(self, file_path: str):
        """
        Adds a new file entity to the tool
        :param file_path:
        :return:
        """
        file: File = File(file_path, self.folder)
        self.all_files.append(file)

    def verify(self):
        """
        Checks if the tool contains actual files and is therefore a valid /verified tool
        If no file is associated to the tool, the tool folder will be deleted.
        If more than one file is associated to the tool a merged file will be added
        :return:
        """
        if len(self.all_files) == 0:
            Folder_Management.remove_folder(self.folder)
            self.verified = False
            logging.info(f"Tool {self.name} does not contain any files. The tool will not evaluated.")

        self.verified_files = [file for file in self.all_files if file.verified]
        self.excluded_files = [file for file in self.all_files if not file.verified]

        if Config.DEBUG:
            logging.info(
                f"Tool contains {len(self.excluded_files)} excluded files and {len(self.verified_files)} verified files.")

        if len(self.verified_files) == 0:
            Folder_Management.remove_folder(self.folder)
            self.verified = False
            logging.info(f"Tool {self.name} does not contain at least one file that is verified")
            logging.info(f"The tool will not evaluated and the folder will be cleanup up.")

        # Add a merged file to the tool.
        if len(self.verified_files) > 1:
            self.__add_merged_file()

    def free_memory(self):
        """
        Frees memory if the memory saving mode is active
        :return:
        """

        if not Config.MEMORY_SAVING_MODE:
            return

        logging.info("Cleaning memory...")
        for file in self.verified_files:
            file.free_memory()

        sleep(1)

    def evaluate(self):
        """
        Handles the evaluation of a tool
        :return:
        """
        print()
        logging.info(f"Evaluating tool {self.name}...")
        # Load data for each file of the tool because it was not loaded at the start
        if Config.MEMORY_SAVING_MODE:
            for file in self.verified_files:
                file.load_memory_sensitive_data()

        # Evaluate the files
        for file in self.verified_files:
            logging.info(f"Evaluating file {file.name}...")
            # Iterate through all label that are present in the df

            if len(file.detected_labels) == 0:
                logging.warn(f"No labels detected for file {file.name}")

            for label in file.detected_labels:
                file.predict(label)
                file.predict_splits(label)
                file.pca_analysis(label)
                # TODO: Readd that
                # file.k_means(label)

            # Copy the source file to the results folder
            # If its a merged file use the virtual one.
            if not file.merged_file:
                shutil.copy(file.path, file.folder)
            else:
                file.raw_df.to_csv(Path.joinpath(file.folder, "raw_df.csv"), index=False)

            file.evaluated = True

    def prepare_additional_files(self):
        """
        Prepare additional files after the first evaluation. E.g. merge only best performing versions instead of all.
        """
        if len(self.verified_files) <= 1:
            return

        print()
        logging.info("Preparing additional files...")
        self.__prepare_best_performing_version_merged_file()

    def evaluate_additional_files(self):
        """
        Evaluate all data sets and files which are create after the first evaluation
        """
        for file in self.verified_files:
            if file.evaluated:
                continue

            logging.info(f"Evaluating file {file.name}...")
            for label in file.detected_labels:
                # Predict values for single files
                file.predict(label)
                file.predict_splits(label)
                file.pca_analysis(label)
                file.evaluated = True

    def create_simple_data_sets(self):
        """
        Creates the simple data frame for each file, using the best performing tool as reference
        """
        for file in self.verified_files:
            logging.info(f"Creating simple data sets from for version {file.name}")
            file.create_simple_data_set()
            file.evaluate_simple_data_set()
            # TODO: add violin plot for test score distribution

    def generate_reports(self):
        """
        Generate csv and tsv files for the tool and all files associated to the tool
        :return:
        """
        logging.info("Generating report files...")

        # Generate file specific reports
        for file in self.verified_files:
            file.generate_reports()

        for label in self.files_label_overview["Label"].unique():
            data = Data_Frame_Helper.get_label_data(self.files_label_overview, label)

            if data.empty:
                continue

            data.sort_values(by='Test Score', ascending=False, inplace=True)
            data.to_csv(os.path.join(self.folder, f"{label}_overview_files_report.csv"),
                        index=False)

        logging.info("All reports generated.")
        sleep(1)

    def generate_plots(self):
        """
        Generates all plots
        :return:
        """

        # Generate plots for each file associated to the tool
        for file in self.verified_files:
            file.generate_plots()

        self.__plot_prediction_score_overview()
        self.__plot_statistics()

    def generate_overview_data_sets(self):
        """
        Creates the overview data sets
        """

        # Clean dictionary
        self.files_label_overview = pd.DataFrame()

        for file in self.verified_files:
            for label in file.evaluation_results["Label"].unique():
                data = Data_Frame_Helper.get_label_data(file.evaluation_results, label)

                if data.empty:
                    continue

                self.files_label_overview = self.files_label_overview.append(data)

    # TODO: Return the file instead of the data row
    def get_best_performing_version(self, label: str):
        """
        Returns the best performing version of the tool for the specific label
        """

        data = Data_Frame_Helper.get_label_data(self.files_label_overview, label)

        if data.empty:
            return None

        # Create a copy to manipulate the data
        data = data.reset_index()
        row_id = data['Test Score'].argmax()
        return data.loc[row_id]

    # TODO: Return the file instead of the data row
    def get_worst_performing_version(self, label: str):
        """
        Returns the worst performing version of the tool
        """

        data = Data_Frame_Helper.get_label_data(self.files_label_overview, label)

        if data.empty:
            return None

        data = data.reset_index()
        row_id = data['Test Score'].argmin()
        return data.loc[row_id]

    def calculate_tool_statistics(self):
        """
        Calculates mean, median, and correlation
        """

        # File evaluation
        for file in self.verified_files:
            for label in file.evaluation_results["Label"].unique():
                data = Data_Frame_Helper.get_label_data(file.evaluation_results, label)

                if data.empty:
                    continue

                # TODO: Check correlation calculation
                self.statistics = self.statistics.append(
                    {
                        "Data": "Whole",
                        "Label": label,
                        "Mean": data["Test Score"].mean(),
                        "Median": data["Test Score"].median(),
                        "Correlation": data["Test Score"].astype(float).corr(
                            data["Processed Feature Count"].astype(float))
                    }, ignore_index=True)
        # Splits
        for file in self.verified_files:
            for label in file.split_evaluation_results["Label"].unique():
                data = Data_Frame_Helper.get_label_data(file.split_evaluation_results, label)

                if data.empty:
                    continue

                self.statistics = self.statistics.append(
                    {
                        "Data": "Split",
                        "Label": label,
                        "Mean": data["Test Score"].mean(),
                        "Median": data["Test Score"].median(),
                        "Correlation": data["Test Score"].astype(float).corr(
                            data["Processed Feature Count"].astype(float))
                    }, ignore_index=True)

        # simple df evaluation
        for file in self.verified_files:
            for label in file.simple_dfs_evaluation["Label"].unique():
                data = Data_Frame_Helper.get_label_data(file.simple_dfs_evaluation, label)

                if data.empty:
                    continue

                self.statistics = self.statistics.append(
                    {
                        "Data": "Simple",
                        "Label": label,
                        "Mean": data["Test Score"].mean(),
                        "Median": data["Test Score"].median(),
                        "Correlation": data["Test Score"].astype(float).corr(
                            data["Processed Feature Count"].astype(float))
                    }, ignore_index=True)

    def __plot_statistics(self):
        """
        Plots the tool statistics
        """
        for label in self.statistics['Label'].unique():
            data = Data_Frame_Helper.get_label_data(self.statistics, label)
            # Remove outliers

            data = data[np.abs(data["Mean"] - data["Mean"].mean()) <= (3 * data["Mean"].std())]

            data = pd.melt(data, id_vars=['Data'], value_vars=['Mean', 'Median', 'Correlation'])
            data["value"].fillna(0)

            ax = sns.violinplot(x="variable", y="value", hue="Data", data=data)
            ax.set(xlabel="Statistics", ylabel='Value')
            fig = ax.get_figure()

            fig.savefig(
                Path.joinpath(self.folder, f"{label}_test_score_statistics.jpg"),
                bbox_inches="tight")
            fig.clf()
            plt.close('all')

    def __plot_prediction_score_overview(self):
        """"
        Plots an overview
        """
        for label in self.files_label_overview["Label"].unique():

            data = Data_Frame_Helper.get_label_data(self.files_label_overview, label)

            if data.empty:
                continue

            ax = sns.barplot(x="File Name", y="Test Score", data=data,
                             palette="Set3")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
            fig = ax.get_figure()

            fig.savefig(Path.joinpath(self.folder, f"{label}_prediction_overview.jpg"), bbox_inches="tight")
            fig.clf()
            plt.close('all')

    #### Merged files

    def __add_merged_file(self):
        """
        Merges the raw data sets of all verified versions into a big one.
        Assuming that all single files are valid this merged one should be valid too.
        The new merged dataset is considered the raw data frame for the new create file object.
        :return:
        """
        merged_raw_df = []
        for file in self.verified_files:
            df = file.raw_df.copy()
            df["Version"] = f"{file.version}"
            merged_raw_df.append(df)

        merged_files_raw_df = pd.concat(merged_raw_df, join='inner')
        merged_file = File("merged_tool", self.folder, merged_files_raw_df)
        self.verified_files.append(merged_file)

    def __prepare_best_performing_version_merged_file(self):
        """
        Prepares a merged data set which contains only data from version with a test score > 0.6
        """

        for label in self.files_label_overview["Label"].unique():
            best_versions_df = []

            data = Data_Frame_Helper.get_label_data(self.files_label_overview, label)

            if data.empty:
                continue

            quantile = data["Test Score"].quantile(0.7)
            best_performing = data[data['Test Score'] >= quantile]['File Name'].tolist()

            for file in self.verified_files:
                if file.name in best_performing and not file.merged_file:
                    df = file.raw_df.copy()
                    df["Version"] = file.version
                    best_versions_df.append(df)

            if len(best_versions_df) <= 1:
                if Config.DEBUG:
                    logging.debug("Best performing data sets length is <= 1. Skipping...")
                return

            best_version_files_raw_df = pd.concat(best_versions_df, join='inner')
            best_version_merged_file = File(f"{label}_best_version_merged_file", self.folder, best_version_files_raw_df)
            self.verified_files.append(best_version_merged_file)

    #### End Merged Files
