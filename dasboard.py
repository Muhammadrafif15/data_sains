import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import seaborn as sns
import math
from babel.numbers import format_currency
sns.set(style='dark')


def create_delivery_status(df_orders):
    delivery_status = df_orders.groupby(by='delivery_status').order_id.nunique().reset_index()
    delivery_status.rename(columns={"order_id" : "order_count"}, inplace=True)

    return delivery_status

def create_delivery_time(df_orders):
    delivery_time = df_orders.groupby(by='delivery_time_days').order_id.nunique().reset_index()
    delivery_time.rename(columns={'order_id' : 'order_count'}, inplace=True)

    return delivery_time

def create_delivery_delay(df_orders):
    delay = df_orders.groupby(by='delay_status').order_id.nunique().reset_index()
    delay.rename(columns={'order_id' : 'order_count'}, inplace=True)

    return delay

def create_daily_stat(df_orders, df_order_item):
    columns = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']
    for column in columns:
        df_orders[column] = pd.to_datetime(df_orders[column])

    df_orders['day_of_week'] = df_orders['order_purchase_timestamp'].dt.dayofweek
    df_orders['day_name'] = df_orders['order_purchase_timestamp'].dt.day_name()

    daily_purchases = df_orders.merge(df_order_item, on='order_id')

    daily_stat = daily_purchases.groupby(by='day_name').agg({
    "order_id" : "count",
    "price" : "sum",
    "freight_value" : "sum"
    }).reset_index()

    daily_stat.columns = ['day_name', 'total_order', 'total_sales', 'total_shipping']
    daily_stat['avg_value'] = daily_stat['total_sales'] / daily_stat['total_order'] 
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_stat['day_name'] = pd.Categorical(daily_stat['day_name'], categories=day_order, ordered=True)
    daily_stat = daily_stat.sort_values('day_name')

    return daily_stat

def create_rfm_analisis(df_orders, df_order_item):
    df_orders = df_orders[df_orders["delivery_status"] == "Pesanan Selesai"]
    ordered_df = df_orders.merge(
    df_order_item,
    left_on="order_id",
    right_on="order_id"
    )

    rfm_df = ordered_df.groupby(by="customer_id", as_index=False).agg({
    "order_approved_at" : "max",
    "order_id" : "nunique",
    "price" : "sum"
    })

    rfm_df.columns = ["customer_id", "max_order_timestamp", "frequency", "monetary"]
    rfm_df["max_order_timestamp"] = pd.to_datetime(rfm_df["max_order_timestamp"])

    rfm_df["max_order_timestamp"] = rfm_df["max_order_timestamp"].dt.date
    recent_date = df_orders["order_approved_at"].dt.date.max()

    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: abs((recent_date - x).days))
    
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)

    return rfm_df

def create_rfm_segment(rfm_df):
    rfm_df["f_rank"] = rfm_df["frequency"].rank(ascending=True)
    rfm_df["r_rank"] = rfm_df["recency"].rank(ascending=False)
    rfm_df["m_rank"] = rfm_df["monetary"].rank(ascending=False)

    rfm_df["r_rank_norm"] = (rfm_df["r_rank"] / rfm_df["r_rank"].max())*100
    rfm_df["f_rank_norm"] = (rfm_df["f_rank"] / rfm_df["f_rank"].max())*100
    rfm_df["m_rank_norm"] = (rfm_df["m_rank"] / rfm_df["m_rank"].max())*100

    rfm_df.drop(columns=['f_rank', 'r_rank', 'm_rank'], inplace=True)

    rfm_df['RFM_Score'] = 0.15*rfm_df['r_rank_norm']+0.28 *  rfm_df['f_rank_norm']+0.57*rfm_df['m_rank_norm']
    rfm_df['RFM_Score'] *= 0.05
    rfm_df = rfm_df.round(2)
    rfm_df[['customer_id', 'RFM_Score']].head(10)

    rfm_df['RFM_segmentasi'] = np.where(rfm_df['RFM_Score'] > 4.5, "Top Customer", (
    np.where(rfm_df['RFM_Score'] > 4, "High Value Customer", (
        np.where(rfm_df['RFM_Score'] > 3, "Medium Value Customer", (
            np.where(rfm_df['RFM_Score'] > 1.6, "Low Value Customer", "Lost Customer")))))))

    rfm_df[['customer_id', 'RFM_Score', 'RFM_segmentasi']].head(10)
    customer_segment = rfm_df.groupby(by='RFM_segmentasi', as_index=False).customer_id.nunique()

    return customer_segment

#load data

df_orders = pd.read_csv("main_df.csv")
df_orders_ori = pd.read_csv("orders_df_ori.csv")
df_order_item = pd.read_csv("order_item.csv")

delivery_status = create_delivery_status(df_orders_ori)
delivery_time = create_delivery_time(df_orders_ori)
deliver_delay = create_delivery_delay(df_orders_ori)
daily_stat = create_daily_stat(df_orders, df_order_item)
rfm_analisis = create_rfm_analisis(df_orders, df_order_item)
rfm_segment = create_rfm_segment(rfm_analisis)

st.title("E-Commerce Public Dataset Customer and Delivery")
st.subheader('Daily Orders')

col1, col2 = st.columns(2)

with col1:
    total_orders = daily_stat.total_order.sum()
    st.metric("Total orders", value=total_orders)

with col2:
    total_revenue = format_currency(daily_stat.total_sales.sum(), "USD", locale='es_us') 
    st.metric("Total Revenue", value=total_revenue)

# daily activity order of week 

tap1, tap2, tap3, tap4 = st.tabs(["Order", "Sales", "Average Order", "Shipping Cost"])
colors = ["#4c5c5a", "#a8a6a5", "#a8a6a5", "#a8a6a5", "#a8a6a5", "#a8a6a5", "#a8a6a5"]

with tap1:

    with st.container():
        avg_order = round(daily_stat.total_order.mean(), 1)
        st.metric("Average Order (week)", value=avg_order)

    st.subheader("Total Orders by Day of Week")
    fig, ax = plt.subplots(figsize=(20, 8))

    sns.barplot(data=daily_stat.sort_values(by='day_name',ascending=False), x='day_name', y='total_order', ax=ax, palette=colors)
    #   ax.set_title('Total Orders by Day of Week', loc='center', fontsize=25)
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='y', labelsize=20)
    ax.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

with tap2:

    with st.container():
        avg_sales = round(daily_stat.total_sales.mean(), 1)
        st.metric("Average Sales (week)", value=avg_sales)
        st.subheader("Total Sales by Day of Week")
        fig, ax = plt.subplots(figsize=(20, 8))

        sns.barplot(data=daily_stat.sort_values(by='total_sales', ascending=False), x='day_name', y='total_sales', ax=ax, palette=colors)
        #ax.set_title('Total Sales by Day of Week(million)', fontsize=30, loc='center')
        ax.set_ylabel(None)
        ax.set_xlabel(None)
        ax.tick_params(axis='y', labelsize=20)
        ax.tick_params(axis='x', labelsize=20)
        st.pyplot(fig)

with tap3:

    with st.container():
        avg_value = round(daily_stat.avg_value.mean(), 1)
        st.metric("Average Order (week)", value=avg_value)

    st.subheader("Average Order Value by Day of Week")
    fig, ax = plt.subplots(figsize=(20, 8))
    sns.barplot(data=daily_stat.sort_values(by='avg_value', ascending=False), x='day_name', y='avg_value', ax=ax, palette=colors)
    #ax.set_title('Average Order Value by Day of Week', fontsize=30, loc='center')
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='y', labelsize=20)
    ax.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)


with tap4:

    with st.container():
        avg_shipping = round(daily_stat.total_shipping.mean(), 1)
        st.metric("Average Shipping (week)", value=avg_shipping)

    st.subheader("Total Shipping Cost by Day of Week")

    fig, ax = plt.subplots(figsize=(20, 8))
    sns.barplot(data=daily_stat.sort_values(by='total_shipping', ascending=False), x='day_name', y='total_shipping', ax=ax, palette=colors)
    #ax.set_title('Total Shipping Cost by Day of Week', fontsize= 30, loc='center')
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='y', labelsize=20)
    ax.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

# RFM analisis lanjutan

with st.container():
    st.subheader("Best Customer Based on RFM Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_recency = round(rfm_analisis.recency.mean(), 1)
        st.metric("Average Recency (days)", value=avg_recency)

    with col2:
        avg_frequency = round(rfm_analisis.frequency.mean(), 2)
        st.metric("Average Frequency", value=avg_frequency)

    with col3:
        avg_frequency = format_currency(rfm_analisis.monetary.mean(), "USD", locale='es_us') 
        st.metric("Average Monetary", value=avg_frequency)


rfm1, rfm2, rfm3 = st.tabs(['Recency', 'Frequency', 'Monetary'])

with rfm1:
    fig, ax = plt.subplots(figsize=(20, 10))

    sns.barplot(
        data=rfm_analisis.sort_values(by="recency", ascending=True).head(30),
        x="recency",
        y="customer_id",
    )
    ax.set_title("By Recency (days)", loc="center", fontsize=30)
    ax.set_ylabel("Customer ID", fontsize=30)
    ax.set_xlabel("Day", fontsize=30)
    plt.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)
    

with rfm3:
    fig, ax = plt.subplots(figsize=(20, 10))

    sns.barplot(
        data=rfm_analisis.sort_values(by="monetary", ascending=False).head(30),
        y="customer_id",
        x="monetary"
    )
    ax.set_title("By Monetary", loc="center", fontsize=30)
    ax.set_ylabel("Customer ID", fontsize=30)
    ax.set_xlabel("Monetary", fontsize=30)
    plt.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

with rfm2:
    fig, ax = plt.subplots(figsize=(20, 10))
    sns.barplot(
        data=rfm_analisis.sort_values(by="frequency", ascending=False).head(30),
        y="customer_id",
        x="frequency"
    )
    plt.title("By Frequency", loc="center", fontsize=30)
    plt.ylabel("Customer ID", fontsize=30)
    plt.xlabel("Frequency", fontsize=30)
    plt.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

#interaktif fitur dari tanggal penjualan per kategori  produk

def create_product_analisis(product_analisis):
    categoriy_analisis = product_analisis.groupby(by='product_category_name_english', as_index=False).agg({
    'order_id' : 'nunique',
    'order_item_id' : 'sum',
    'price' : 'sum',
    'review_score' : 'mean',
    'order_approved_at' : 'max'
    })
    #categoriy_analisis.head()
    categoriy_analisis.columns = ['nama_kategori', 'banyak_order', 'barang_terjual', 'total_harga', 'review_score', 'order_terakhir']
    return categoriy_analisis

def create_product_tanggal_analisis(product_analisis):
    categoriy_analisis_tanggal = product_analisis.groupby(by='order_approved_at', as_index=False).agg({
    'order_id' : 'nunique',
    'order_item_id' : 'sum'
    })
    categoriy_analisis_tanggal.columns = ['tanggal', 'banyak_penjualan', 'barang_terjual']

    return categoriy_analisis_tanggal

product_analisis = pd.read_csv("product_analisis.csv")

# Berdasarkan filter tanggal

product_analisis["order_approved_at"] = pd.to_datetime(product_analisis["order_approved_at"])

product_analisis.sort_values(by="order_approved_at", inplace=True)
product_analisis.reset_index(inplace=True)


# Filter data
min_date = product_analisis["order_approved_at"].min()
max_date = product_analisis["order_approved_at"].max()

start_date, end_date = st.date_input(
        label='Rentang Waktu',min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

product_analisis = product_analisis[(product_analisis["order_approved_at"] >= str(start_date)) & 
                (product_analisis["order_approved_at"] <= str(end_date))]

categoriy_analisis = create_product_analisis(product_analisis)
categoriy_analisis_tanggal = create_product_tanggal_analisis(product_analisis)

print(categoriy_analisis.columns)

with st.container():
    st.header("Kategori Produk Analisis")

    col1, col2, col3 = st.columns(3)

    with col1:
        sum_order = categoriy_analisis.banyak_order.sum()
        st.metric("Jumlah Pembelian", value=sum_order)

    with col2:
        sum_terjual = categoriy_analisis.barang_terjual.sum()
        st.metric("Jumlah Barang", value=sum_terjual)

    with col3:
        sum_harga = format_currency(categoriy_analisis.total_harga.sum(), 'USD', locale='en_us')
        st.metric("Total Harga", value=sum_harga)

    col4, col5, col6 = st.columns(3)

    # categoriy_analisis = np.nan_to_num(categoriy_analisis, nan=0.0)

    with col4:
        avg_order = round(categoriy_analisis.banyak_order.mean(), 2)
        st.metric("Rata-Rata Pembelian", value=avg_order)

    with col5:
        avg_terjual = round(categoriy_analisis.barang_terjual.mean(), 2)
        st.metric("Rata-Rata Jumlah Barang", value=avg_terjual)

    with col6:  
        avg_harga = round(categoriy_analisis.total_harga.mean(), 2)
        st.metric("Rata-Rata Total Harga", value=avg_harga)

    with st.container():
        fig, ax = plt.subplots(figsize=(7,4))
        sns.barplot(
            data=categoriy_analisis.sort_values(by='banyak_order', ascending=False).head(20),
            y='nama_kategori',
            x='banyak_order'
        )
        ax.set_title("Banyak Penjualan Perkategori")
        ax.set_ylabel(None)
        ax.set_xlabel(None)
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(7,4))
        sns.lineplot(
            data=categoriy_analisis_tanggal,
            x='tanggal',
            y='banyak_penjualan'
        )
        ax.set_title("Banyak penjulan")
        ax.set_ylabel(None)
        ax.set_xlabel(None)

        st.pyplot(fig)
    
    with st.container():
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(
            data=categoriy_analisis.sort_values(by='barang_terjual', ascending=False).head(10),
            y='nama_kategori',
            x='barang_terjual',
        )
        ax.set_ylabel(None)
        ax.set_xlabel(None)
        ax.set_title('Barang Terjual')

        fig, ax = plt.subplots(figsize=(7,4))
        sns.lineplot(
            data=categoriy_analisis_tanggal,
            x='tanggal',
            y='barang_terjual'
            )
        ax.set_title("Banyak Barang Terjual")
        ax.set_ylabel(None)
        ax.set_xlabel(None)
        st.pyplot(fig)
    
        fig, ax = plt.subplots(figsize=(7, 3))
        sns.barplot(
        data=categoriy_analisis.sort_values(by='total_harga', ascending=False).head(15),
            y='nama_kategori',
            x='total_harga'
        )
        plt.ylabel(None)
        plt.xlabel(None)
        plt.title('Total Harga per Kategori')
        st.pyplot(fig)

# delivery status order
colors = sns.color_palette("deep")

st.subheader("Delivery Order Status")

with st.container():
    fig, ax = plt.subplots(figsize=(20, 10))
    sns.barplot(
        data=delivery_status.sort_values(by="order_count",ascending=False),
        x="order_count",
        y="delivery_status",
    )
    ax.set_title("Delivery Status", loc="center", fontsize=30)
    ax.set_ylabel(None)
    ax.set_xlabel(None)
    ax.tick_params(axis='y', labelsize=20)
    ax.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

with st.container():
    fig, ax = plt.subplots(figsize=(20, 10))
    sns.barplot(
        data=delivery_time.sort_values(by="delivery_time_days", ascending=True).head(20),
        x='delivery_time_days',
        y='order_count',  
    )
    ax.set_title("Many Delivery Duration(day)", loc='center', fontsize=30)
    ax.set_xlabel("Delivery Time(day)", fontsize=30)
    ax.set_ylabel("Number Delivery", fontsize=30)
    ax.tick_params(axis='y', labelsize=20)
    ax.tick_params(axis='x', labelsize=20)
    st.pyplot(fig)

with st.container():
    explode = (0, 0.1, 0)
    fig, ax = plt.subplots(figsize=(10, 10))
    plt.pie(
        deliver_delay['order_count'],
        labels=deliver_delay['delay_status'],
        autopct='%1.1f%%',
        colors=colors,
        shadow={'ox': -0.04, 'edgecolor': 'none', 'shade': 0.9}, 
        startangle=90,
        textprops={'size': 'large'},
        explode=explode
    )
    ax.set_title("Delivery Time Delay", loc="center", fontsize=20)
    st.pyplot(fig)

    st.caption("Muhammad Rafif Rizqullah")