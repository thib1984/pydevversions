from setuptools import setup

setup(
    name="pydevversions",
    version="1.5.0",
    description="pydevversions game in terminal",
    long_description="The complete description/installation/use/FAQ is available at : https://github.com/thib1984/pydevversions#readme",
    url="https://github.com/thib1984/pydevversions",
    author="thib1984",
    author_email="thibault.garcon@gmail.com",
    license="MIT",
    license_files="LICENSE.txt",
    packages=["pydevversions"],
    install_requires=["tqdm", "rich", "pyyaml"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "pydevversions=pydevversions.__init__:pydevversions"
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    include_package_data=True,
    package_data={
        "pydevversions": ["apps.yaml"],
    },    
)
