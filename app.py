import streamlit as st
import pandas as pd 
import seaborn as sns
import matplotlib.pyplot as plt

df = sns.load_dataset("penguins")


fig, ax = plt.subplots()
sns.scatterplot(data=df, x="sex", y="bill_length_mm", hue="bill_length_mm", ax=ax)
 
st.title("Penguin Dataset")
st.header("This is for the Scatter plot for it")
st.pyplot(fig)
st.markdown("**The Table of Penguins**")
 
st.dataframe(df.head())
st.table(df)

#bill_lenth_mm 
#sex