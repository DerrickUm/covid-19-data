import os
import pandas as pd
from cowidev.utils.web import request_json
from cowidev.utils.utils import get_project_dir
from cowidev.utils.clean import clean_date_series


class India:
    location: str = "India"
    units: str = "samples tested"
    source_label: str = "Indian Council of Medical Research"
    source_url: str = "https://raw.githubusercontent.com/datameet/covid19/master/data/icmr_testing_status.json"
    source_url_ref: str = "https://github.com/datameet/covid19"
    notes: str = "Made available by DataMeet on GitHub"
    rename_columns: dict = {"report_time": "Date", "samples": "Cumulative total"}

    def read(self) -> pd.DataFrame:
        data = request_json(self.source_url)
        data = [x["value"] for x in data["rows"]]
        df = pd.DataFrame.from_records(data, columns=["report_time", "samples"])  # Load only columns needed
        df["report_time"] = clean_date_series(df["report_time"], "%Y-%m-%dT%H:%M:%S.%f%z")  # Clean date
        return df

    def pipe_rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=self.rename_columns)

    def pipe_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(
            **{
                "Country": self.location,
                "Units": self.units,
                "Source label": self.source_label,
                "Source URL": self.source_url_ref,
                "Notes": self.notes,
            }
        )

    def pipe_filter_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.drop_duplicates(subset="Cumulative total")
            .drop_duplicates(subset="Date")
            .drop(df[df["Date"] == "2021-09-02"].index)
        )

    def pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.pipe(self.pipe_rename_columns).pipe(self.pipe_metadata).pipe(self.pipe_filter_rows)

    def export(self):
        path = os.path.join(
            get_project_dir(), "scripts", "scripts", "testing", "automated_sheets", f"{self.location}.csv"
        )
        df = self.read().pipe(self.pipeline)
        df.to_csv(path, index=False)


def main():
    India().export()


if __name__ == "__main__":
    main()
