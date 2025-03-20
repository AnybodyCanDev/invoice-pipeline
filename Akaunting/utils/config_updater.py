# utils/config_updater.py
import config


def update_bill_id_in_config(new_bill_id):
    """
    Update the BILLS_ENDPOINT in config.py with the new bill_id.
    """
    config.BILLS_ENDPOINT = f"{config.ZOHO_API_DOMAIN}/books/v3/bills/{new_bill_id}?organization_id={config.ZOHO_ORG_ID}"
    with open("config.py", "r") as file:
        lines = file.readlines()

    with open("config.py", "w") as file:
        for line in lines:
            if line.startswith("BILLS_ENDPOINT"):
                file.write(f'BILLS_ENDPOINT = "{config.BILLS_ENDPOINT}"\n')
            else:
                file.write(line)

    print(f"Updated BILLS_ENDPOINT in config.py to: {config.BILLS_ENDPOINT}")
