import pkgutil

modules = [
    "smartapi",
    "smartapi_python",
    "SmartApi",
    "smartapi_python",
    "SmartApi.smartConnect",
    "SmartApi.smartConnect"
]

for m in modules:
    print(m, "->", pkgutil.find_loader(m))
