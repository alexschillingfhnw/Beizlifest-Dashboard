import streamlit as st
from pathlib import Path
import csv
from datetime import datetime
import random
import pandas as pd
import psycopg2

# --- Constants ---
CSV_PATH = Path("bestellungen.csv")
CATEGORY_COLORS = {
    "BIER": "#e0f7fa",
    "DIVERSES": "#f1f8e9",
    "LONGDRINKS": "#fff3e0",
    "SHOTS": "#fce4ec",
    "SOFTGETRÄNKE": "#e8eaf6",
    "ESSEN": "#f3e5f5"
}
PRODUCTS = {
    "BIER": [("Feldschlösschen", 5), ("Pabst", 5), ("Zöndstoff", 5)],
    "DIVERSES": [
        ("Smirnoff Ice", 6), ("Weisswein Glas", 6), ("Weisswein Flasche", 36),
        ("Gespirtzter Weisswein", 7), ("Cüpli / Hugo", 6), ("Aperol Spritz", 10)
    ],
    "LONGDRINKS": [("Whisky", 10), ("Vodka", 10), ("Gin", 10), ("Captain", 10), ("Flying Hirsch", 10)],
    "SHOTS": [("Jägermeister", 5), ("Saurer Apfel", 5), ("Feigling", 5), ("Berliner Luft", 5)],
    "SOFTGETRÄNKE": [
        ("Mineral mit/ohne", 2), ("Sprite", 4), ("Coca Cola", 4), ("Ice Tea", 4),
        ("Bitterlemon / Tonic", 4), ("Ginger Ale", 4), ("El Tony", 5),
        ("Orangensaft", 5), ("Red Bull", 5)
    ],
    "ESSEN": [("Plättli", 18), ("Hot Dog", 5)]
}

# --- Database Initialization ---
def init_db():
    conn = psycopg2.connect(st.secrets["db_url"])
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_number TEXT,
            timestamp TEXT,
            category TEXT,
            product TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL
        )
        """
    )
    conn.commit()
    conn.close()

# --- Session State Initialization ---
def init_state():
    if 'orders' not in st.session_state:
        st.session_state.orders = {}
    if 'total' not in st.session_state:
        st.session_state.total = 0

# --- Order Actions ---
def add_order(category: str, product: str, price: int):
    key = (category, product)
    orders = st.session_state.orders
    if key in orders:
        orders[key]['count'] += 1
    else:
        orders[key] = {'category': category, 'product': product, 'count': 1, 'price': price}
    st.session_state.total += price

def reset_order():
    st.session_state.orders = {}
    st.session_state.total = 0

def submit_order():
    order_num = datetime.now().strftime("%Y%m%d%H%M%S") + f"{random.randint(100,999)}"
    ts = datetime.now().isoformat()

    # CSV backup (optional, for local audit)
    file_exists = CSV_PATH.exists()
    with CSV_PATH.open('a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["order_number", "timestamp", "category", "product", "quantity", "unit_price", "total_price"])
        for (_, _), data in st.session_state.orders.items():
            writer.writerow([
                order_num,
                ts,
                data['category'],
                data['product'],
                data['count'],
                data['price'],
                data['count'] * data['price']
            ])

    # Remote DB insert
    try:
        conn = psycopg2.connect(st.secrets["db_url"])
        c = conn.cursor()
        for (_, _), data in st.session_state.orders.items():
            c.execute(
                """
                INSERT INTO orders(order_number, timestamp, category, product, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    order_num,
                    ts,
                    data['category'],
                    data['product'],
                    data['count'],
                    data['price'],
                    data['count'] * data['price']
                )
            )
        conn.commit()
        conn.close()
        st.success(f"Order {order_num} submitted and saved!")
        reset_order()
    except Exception as e:
        st.error(f"Error saving to database: {e}")

# --- UI Components ---
def render_summary():
    st.subheader("Aktuelle Bestellung")
    if st.session_state.orders:
        rows = []
        for (_, _), data in st.session_state.orders.items():
            rows.append({
                "Kategorie": data['category'],
                "Produkt": data['product'],
                "Menge": data['count'],
                "Einzelpreis": f"{data['price']} CHF",
                "Gesamt": f"{data['count'] * data['price']} CHF"
            })
        df = pd.DataFrame(rows)
        st.table(df)
        st.markdown(f"**Gesamt: {st.session_state.total} CHF**")
    else:
        st.info("Noch keine Bestellung.")

# --- Main App ---
def main():
    init_db()
    init_state()

    # Custom CSS for tight buttons
    st.markdown("""
    <style>
        div.stButton { margin:0; padding:0 }
        div.stButton > button { width:100%; margin:2px 0; padding:4px 0; line-height:2 }
    </style>
    """, unsafe_allow_html=True)

    st.title("Beizlifest Dashboard")
    render_summary()
    c1, c2 = st.columns(2)
    c1.button("Bestellung zurücksetzen", on_click=reset_order)
    c2.button("Bestellung absenden", on_click=submit_order)
    st.markdown("---")

    # Product Catalog
    left, right = st.columns(2)

    with left:
        for cat in ["BIER", "DIVERSES", "LONGDRINKS"]:
            color = CATEGORY_COLORS.get(cat, "#ffffff")
            st.markdown(
                f"<div style='background-color:{color};padding:4px;border-radius:4px;margin-bottom:4px'>"
                f"<h3 style='margin:0;text-align:center'>{cat}</h3></div>", unsafe_allow_html=True
            )
            for prod, price in PRODUCTS[cat]:
                st.button(
                    f"{prod} ({price})",
                    key=f"btn_{cat}_{prod}",
                    on_click=add_order,
                    args=(cat, prod, price)
                )

    with right:
        for cat in ["SHOTS", "SOFTGETRÄNKE", "ESSEN"]:
            color = CATEGORY_COLORS.get(cat, "#ffffff")
            st.markdown(
                f"<div style='background-color:{color};padding:4px;border-radius:4px;margin-bottom:4px'>"
                f"<h3 style='margin:0;text-align:center'>{cat}</h3></div>", unsafe_allow_html=True
            )
            for prod, price in PRODUCTS[cat]:
                st.button(
                    f"{prod} ({price})",
                    key=f"btn_{cat}_{prod}",
                    on_click=add_order,
                    args=(cat, prod, price)
                )

if __name__ == '__main__':
    main()
