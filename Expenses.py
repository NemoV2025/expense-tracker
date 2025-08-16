# ---  Import Required Libraries ---
from shiny import App, ui, render, reactive  # Shiny web components
import pandas as pd                          # Data handling
import matplotlib.pyplot as plt              # For pie chart
import pdfplumber                            # For reading PDFs
import io                                    # For handling in-memory files

# ---  Define a basic function to clean and process the bank statement ---
def clean_bank_statement(file, filetype):
    if filetype == "csv":
        df = pd.read_csv(file)
    elif filetype == "pdf":
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        # Parse each line into columns
        rows = []
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                date = parts[0]
                amount = parts[-1].replace("$", "").replace(",", "")
                description = " ".join(parts[1:-1])
                rows.append([date, description, amount])
        df = pd.DataFrame(rows, columns=["Date", "Description", "Amount"])
    else:
        return pd.DataFrame()

    #  Clean and transform the data
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Amount", "Date"], inplace=True)
    df["Category"] = "Uncategorized"

    #  Auto-categorization
    CATEGORY_KEYWORDS = {
        "Fees": ["fee", "charge", "maintenance"],
        "Transfer": ["wire", "transfer", "zelle", "venmo", "paypal"],
        "Dining": ["restaurant", "cafe", "starbucks", "coffee"],
        "Groceries": ["grocery", "walmart", "trader", "whole", "amazon"],
        "Rent": ["rent", "lease", "apartment", "commons"],
        "College Tuition": ["tuition", "college", "university", "uni", "school"],
        "Credit Card": ["crd"],
        "Utilities": ["electric", "water", "gas", "pge", "comcast"],
        "Shopping": ["purchase", "store", "mall"]
    }

    def categorize(desc):
        desc = desc.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(word in desc for word in keywords):
                return category
        return "Uncategorized"

    df["Category"] = df["Description"].apply(categorize)
    return df

# ---  Define the Web Interface ---
app_ui = ui.page_sidebar(
    ui.sidebar(  
        ui.input_file("upload", "Upload Bank Statement", accept=[".csv", ".pdf"]),
        ui.tags.hr(),
        
    ),
    ui.div(  
        ui.output_table("cleaned_table"),
        ui.output_plot("spending_pie")
    ),
    title="Monthly Spend Tracker"
)


# ---  Define Server Logic ---
def server(input, output, session):
    @reactive.Calc
    def processed_data():
        fileinfo = input.upload()
        if not fileinfo:
            return pd.DataFrame()
        file = fileinfo[0]
        ext = file["name"].split(".")[-1].lower()
        f = open(file["datapath"], "rb") if ext == "pdf" else open(file["datapath"], "r", encoding="utf-8")
        return clean_bank_statement(f, ext)

    @output
    @render.table
    def cleaned_table():
        df = processed_data()
        return df if not df.empty else pd.DataFrame({"Upload a file to see results": []})

    @output
    @render.plot
    def spending_pie():
        df = processed_data()
        if df.empty or "Amount" not in df.columns or "Category" not in df.columns:
            return
        df_exp = df[df["Amount"] < 0]
        if df_exp.empty:
            return
        pie_data = df_exp.groupby("Category")["Amount"].sum().abs()
        fig, ax = plt.subplots()
        ax.pie(pie_data, labels=None, autopct=lambda pct: f"{pct:.1f}%" if pct > 1 else "", startangle=85, pctdistance=0.85)
        ax.legend(labels=pie_data.index, title="Categories", loc="center left", bbox_to_anchor=(1, 0.5))
        ax.set_title("Spending Distribution")
        ax.axis("equal")
        return fig

# ---  Launch the App ---
app = App(app_ui, server)
