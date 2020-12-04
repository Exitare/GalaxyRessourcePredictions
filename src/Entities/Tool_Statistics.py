import pandas as pd
from RuntimeContants import Runtime_Folders
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
from Services.Statistics import Tool_Statistics
import numpy as np

sns.set(style="whitegrid")


class ToolStatistics:
    all_tools_evaluations = pd.DataFrame()
    all_tools_performance_difference = pd.DataFrame(columns=["Tool", "Difference", 'Label'])
    multi_tools_performance_difference = pd.DataFrame(columns=["Tool", "Difference", 'Label'])
    whole_data_set_test_scores = pd.DataFrame(columns=["Source", "Tool", "Label", "Mean", "Median", "Correlation"])
    simple_data_set_test_scores = pd.DataFrame(columns=["Source", "Tool", "Label", "Mean", "Median", "Correlation"])
    all_merged_files_evaluations = pd.DataFrame()

    def __init__(self):
        """
        All tool statistic calculation are done here. No plotting!
        """

        self.all_tools_evaluations = Tool_Statistics.get_all_tool_evaluations()
        self.all_tools_performance_difference, self.multi_tools_performance_difference = \
            Tool_Statistics.calculate_tool_performance_difference()
        self.whole_data_set_test_scores = Tool_Statistics.calculate_simple_data_set_statistics()
        self.simple_data_set_test_scores = Tool_Statistics.calculate_whole_data_set_statistics()
        self.all_merged_files_evaluations = Tool_Statistics.get_all_merged_files_evaluations()

    def write_csv_files(self):
        """
        Write all datasets to the evaluation folder
        """
        self.all_merged_files_evaluations.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"all_merged_files_evaluations.csv"), index=False)

        self.all_tools_evaluations.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"all_tools_evaluations.csv"), index=False)

        self.all_tools_performance_difference.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"all_tools_performance_difference.csv"), index=False)

        self.multi_tools_performance_difference.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"multi_tools_performance_difference.csv"), index=False)

        self.whole_data_set_test_scores.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"r2_score_whole_data_sets.csv"), index=False)

        self.simple_data_set_test_scores.to_csv(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"r2_score_simple_data_sets.csv"), index=False)

    def plot(self):
        """
        Calls all plot functions
        """
        self.__plot_tools_performance_difference()
        self.__plot_r2_scores()
        self.__plot_merged_tools_evaluations()

    def __plot_tools_performance_difference(self):
        """
        Plots the tools performance difference
        """
        if not self.all_tools_performance_difference.empty:
            data = self.all_tools_performance_difference[np.abs(
                self.all_tools_performance_difference["Difference"] - self.all_tools_performance_difference[
                    "Difference"].mean()) <= (3 * self.all_tools_performance_difference["Difference"].std())]

            ax = sns.violinplot(x="Label", y="Difference", data=data)
            fig = ax.get_figure()

            fig.savefig(
                Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"test_score_difference_all_tools.jpg"),
                bbox_inches="tight")
            fig.clf()
            plt.close('all')

        if not self.multi_tools_performance_difference.empty:
            data = self.multi_tools_performance_difference[np.abs(
                self.multi_tools_performance_difference["Difference"] - self.multi_tools_performance_difference[
                    "Difference"].mean()) <= (3 * self.multi_tools_performance_difference["Difference"].std())]

            ax = sns.violinplot(x="Label", y="Difference", data=data)
            fig = ax.get_figure()

            fig.savefig(
                Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"test_score_difference_multi_tools.jpg"),
                bbox_inches="tight")
            fig.clf()
            plt.close('all')

    def __plot_r2_scores(self):
        """
        Plot all r2 scores for all tools
        """

        for origin in self.all_tools_evaluations["Origin"]:
            data = self.all_tools_evaluations[self.all_tools_evaluations["Origin"] == origin].copy()

            ax = sns.violinplot(x="Label", y="Test Score", data=data)
            fig = ax.get_figure()

            fig.savefig(
                Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"r2_scores_{origin}.jpg"),
                bbox_inches="tight")
            fig.clf()
            plt.close('all')

    def __plot_merged_tools_evaluations(self):
        """
        Plot the Test Score distribution for only merged versions
        """
        ax = sns.violinplot(x="Label", y="Test Score", data=self.all_merged_files_evaluations)
        fig = ax.get_figure()

        fig.savefig(
            Path.joinpath(Runtime_Folders.EVALUATION_DIRECTORY, f"r2_score_merged_version.jpg"),
            bbox_inches="tight")
        fig.clf()
        plt.close('all')