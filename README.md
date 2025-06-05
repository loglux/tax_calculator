# 💷 UK Tax & NI Calculator

A web application and REST API for calculating UK tax and National Insurance.

🔗 **Live demo:** [https://tax.log7.uk/calculator/](https://tax.log7.uk/calculator/)

---

## ✨ Features

- ⚡️ Modern responsive web interface (**Bootstrap 5**)
- 🇬🇧 England, Wales & Scotland support (regional tax bands)
- 📆 Calculate for multiple tax years (rates in DB, not hardcoded)
- 💼 Handles yearly or hourly income (auto conversion)
- 👓 Blind allowance support
- 🔗 REST API for integrations
- 🗃️ Tax bands, NI rates, and thresholds editable via Django admin
- 🚀 Production-ready deployment

---

## 🚀 Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/<your-github>/tax_calculator.git
    cd tax_calculator
    ```

2. **Create and activate virtual environment:**
    ```sh
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/Mac:
    source .venv/bin/activate
    ```

3. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Run migrations:**
    ```sh
    python manage.py migrate
    ```

5. **Create a superuser (optional, for admin):**
    ```sh
    python manage.py createsuperuser
    ```

---

## 🏃 Running

```sh
python manage.py runserver
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 🧑‍💻 Usage

- **Web:**  
  Use the web form to enter your income, region, year, and other options.

- **API:**  
  `POST` to `/calculate_tax/` with JSON, e.g.:
    ```json
    {
      "income": 45000,
      "income_type": "yearly",
      "tax_year": 2024,
      "is_blind": false,
      "no_ni": false,
      "is_scotland": false,
      "workweek_hours": 40
    }
    ```
  Response: Full breakdown of tax, NI, net income, personal allowance, etc.

---

## 🛠 Technologies

- Django 5
- Django REST Framework
- Bootstrap 5
- Gunicorn (for production)
- Whitenoise (static files)

---

> ⚠️ **Disclaimer:**  
> This calculator provides approximate calculations for UK tax and National Insurance, based on publicly available tax bands and thresholds.  
> It does **not** use HMRC’s official API or methodology, and results may differ from official HMRC calculations.  
> This project is for educational and demonstration purposes only, and is **not** intended as a professional or legally reliable tax tool.

---

## 📄 License

MIT

---

## 🙌 Credits

Developed by Vladislav Sorokin  
[https://tax.log7.uk/calculator/](https://tax.log7.uk/calculator/)


