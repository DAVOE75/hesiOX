from setuptools import setup, find_packages

setup(
    name="sirio",
    version="0.1.0",
    description="Librería para análisis y visualización de datos de los pasajeros del Sirio (Humanidades Digitales)",
    author="David",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas",
        "numpy",
        "plotly",
        "pyvis",
        "folium",
        "selenium",
        "streamlit",
        "branca",
        "matplotlib",
        "kaleido",
        "python-pptx",
        "webdriver-manager",
        "geopy",
        "geopandas",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.9",
)
