import os
from datetime import date, timedelta

import pandas as pd

from cowidev.utils.s3 import upload_to_s3, df_to_s3
from cowidev.utils.utils import get_project_dir, dict_to_compact_json


DATA_DIR = os.path.abspath(os.path.join(get_project_dir(), "public", "data"))


def create_dataset(df, macro_variables):
    """Export dataset as CSV, XLSX and JSON (complete time series)."""
    print("Writing to CSV…")
    filename = os.path.join(DATA_DIR, "owid-covid-data.csv")
    df.to_csv(filename, index=False)
    upload_to_s3(filename, "public/owid-covid-data.csv", public=True)

    print("Writing to XLSX…")
    # filename = os.path.join(DATA_DIR, "owid-covid-data.xlsx")
    # all_covid.to_excel(os.path.join(DATA_DIR, "owid-covid-data.xlsx"), index=False, engine="xlsxwriter")
    # upload_to_s3(filename, "public/owid-covid-data.xlsx", public=True)
    df_to_s3(df, "public/owid-covid-data.xlsx", public=True, extension="xlsx")

    print("Writing to JSON…")
    filename = os.path.join(DATA_DIR, "owid-covid-data.json")
    df_to_json(
        df,
        os.path.join(DATA_DIR, "owid-covid-data.json"),
        macro_variables.keys(),
    )
    upload_to_s3(filename, "public/owid-covid-data.json", public=True)


def create_latest(df):
    """Export dataset as CSV, XLSX and JSON (latest data points)."""
    df = df[df.date >= str(date.today() - timedelta(weeks=2))]
    df = df.sort_values("date")

    latest = [df[df.location == loc].ffill().tail(1).round(3) for loc in set(df.location)]
    latest = pd.concat(latest)
    latest = latest.sort_values("location").rename(columns={"date": "last_updated_date"})

    print("Writing latest version…")
    # CSV
    latest.to_csv(os.path.join(DATA_DIR, "latest", "owid-covid-latest.csv"), index=False)
    upload_to_s3(
        os.path.join(DATA_DIR, "latest", "owid-covid-latest.csv"), "public/latest/owid-covid-latest.csv", public=True
    )
    # XLSX
    df_to_s3(latest, "public/latest/owid-covid-latest.xlsx", public=True, extension="xlsx")
    # JSON
    latest.dropna(subset=["iso_code"]).set_index("iso_code").to_json(
        os.path.join(DATA_DIR, "latest", "owid-covid-latest.json"), orient="index"
    )
    upload_to_s3(
        os.path.join(DATA_DIR, "latest", "owid-covid-latest.json"), "public/latest/owid-covid-latest.json", public=True
    )


def df_to_json(complete_dataset, output_path, static_columns):
    """
    Writes a JSON version of the complete dataset, with the ISO code at the root.
    NA values are dropped from the output.
    Macro variables are normalized by appearing only once, at the root of each ISO code.
    """
    megajson = {}

    static_columns = ["continent", "location"] + list(static_columns)

    complete_dataset = complete_dataset.dropna(axis="rows", subset=["iso_code"])

    for iso in complete_dataset.iso_code.unique():
        country_df = complete_dataset[complete_dataset.iso_code == iso].drop(columns=["iso_code"])
        static_data = country_df.head(1)[static_columns].to_dict("records")[0]
        megajson[iso] = {k: v for k, v in static_data.items() if pd.notnull(v)}
        megajson[iso]["data"] = [
            {k: v for k, v in r.items() if pd.notnull(v)}
            for r in country_df.drop(columns=static_columns).to_dict("records")
        ]

    with open(output_path, "w") as file:
        file.write(dict_to_compact_json(megajson))
