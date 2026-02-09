import requests

url = "https://erp.nnctech.net/api/project3c/employee_task_summary"
headers = {
    "Content-Type": "application/json",
    "X-API-KEY": "3c_dashboard_2024_secret"
}

res = requests.post(url, headers=headers, json={})
print(res.status_code)
print(res.json())
