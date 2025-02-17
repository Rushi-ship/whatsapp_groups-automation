from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import os
from selenium import webdriver

def format_recommendation_message(group_data, group_name, format_type='simple'):
    """Format the stock recommendation message with the given data."""
    try:
        # Add [TEST MODE] prefix for testing groups
        is_test = "testing" in group_name.lower()
        prefix = "[TEST MODE] " if is_test else ""
        
        # Get client name if available, otherwise use "Client"
        client_name = group_data['client_name'].iloc[0] if 'client_name' in group_data.columns else "Client"
        
        message = f"{prefix}Dear {client_name},\n\nHere are your stock recommendations:\n"
        
        if format_type == 'table':
            # Table format
            message += "Sr | Company | NSE ticker | Reco. | Quantity | Approx. CMP Rs. | Approx. Value @ CMP Rs. Lakh | Order Type\n"
            message += "---|---------|------------|--------|----------|----------------|---------------------------|------------\n"
            
            for _, row in group_data.iterrows():
                try:
                    sr = row.get('Sr', '')
                    company = row.get('Company', '')
                    nse_ticker = row.get('NSE ticker', '')
                    reco = row.get('Reco.', '')
                    quantity = row.get('Quantity', '')
                    cmp = row.get('Approx. CMP ₹', '')
                    value = row.get('Approx. Value @CMP ₹ Lakh', '')
                    order_type = row.get('Order Type', '')
                    
                    message += f"{sr} | {company} | {nse_ticker} | {reco} | {quantity} | {cmp} | {value} | {order_type}\n"
                except Exception as e:
                    print(f"Error processing row: {str(e)}")
                    continue
        else:
            # Separate recommendations by BUY and SELL
            buy_recommendations = group_data[group_data['Reco.'].str.upper() == 'BUY']
            sell_recommendations = group_data[group_data['Reco.'].str.upper() == 'SELL']
            
            # Process BUY recommendations
            if not buy_recommendations.empty:
                message += "\n*BUY RECOMMENDATIONS:*\n"
                for _, row in buy_recommendations.iterrows():
                    try:
                        message += f"\n*{row.get('Company', '')} ({row.get('NSE ticker', '')})*"
                        message += f"\n• Quantity: {row.get('Quantity', '')}"
                        message += f"\n• CMP: Rs.{row.get('Approx. CMP ₹', '')}"
                        message += f"\n• Value: Rs.{row.get('Approx. Value @CMP ₹ Lakh', '')} Lakh"
                        message += f"\n• Order Type: {row.get('Order Type', '')}"
                        message += "\n-------------------"
                    except Exception as e:
                        print(f"Error processing BUY row: {str(e)}")
                        continue
            
            # Process SELL recommendations
            if not sell_recommendations.empty:
                message += "\n*SELL RECOMMENDATIONS:*\n"
                for _, row in sell_recommendations.iterrows():
                    try:
                        message += f"\n*{row.get('Company', '')} ({row.get('NSE ticker', '')})*"
                        message += f"\n• Quantity: {row.get('Quantity', '')}"
                        message += f"\n• CMP: Rs.{row.get('Approx. CMP ₹', '')}"
                        message += f"\n• Value: Rs.{row.get('Approx. Value @CMP ₹ Lakh', '')} Lakh"
                        message += f"\n• Order Type: {row.get('Order Type', '')}"
                        message += "\n-------------------"
                    except Exception as e:
                        print(f"Error processing SELL row: {str(e)}")
                        continue

        message += "\n\n*Note:* Please execute orders as early as you can."
        
        if is_test:
            message += "\n\n[THIS IS A TEST MESSAGE - PLEASE IGNORE]"
        
        return message
    except Exception as e:
        print(f"Error formatting message: {str(e)}")
        raise

def send_whatsapp_message(driver, group_name, message):
    """Send a WhatsApp message to a specific group."""
    try:
        print(f"\nTrying to send message to group: {group_name}")
        
        # Wait for and find the search box
        print("Waiting for search box...")
        search_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        
        # Clear the search box properly
        search_box.click()
        time.sleep(1)
        # Use Command+A for Mac (instead of Ctrl+A)
        search_box.send_keys(Keys.COMMAND + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(1)  # Wait after clearing
        
        # Enter group name
        search_box.send_keys(group_name)
        print("Entered group name in search box")
        time.sleep(2)  # Wait for search results
        
        # Try to find and click the group chat
        print("Looking for group in the list...")
        try:
            # Wait for group to be visible and clickable
            group_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//span[contains(@title, '{group_name}')]"))
            )
            time.sleep(1)  # Short wait before clicking
            group_element.click()
            print("Group found and clicked")
            time.sleep(2)  # Wait after clicking group
            
            # Wait for message box
            print("Waiting for message input box...")
            message_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
            )
            
            # Clear message box and wait
            message_box.clear()
            time.sleep(1)
            
            # Type and send message
            print("Typing message...")
            # Split message into lines
            lines = message.split('\n')
            
            # Send first line
            message_box.send_keys(lines[0])
            
            # For each remaining line, simulate Shift+Enter and send the line
            for line in lines[1:]:
                message_box.send_keys(Keys.SHIFT + Keys.ENTER)
                message_box.send_keys(line)
                time.sleep(0.1)  # Small delay between lines
            
            time.sleep(1)  # Wait before clicking send
            
            # Click send button
            print("Looking for send button...")
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']"))
            )
            send_button.click()
            print("Message sent successfully")
            
            # Wait before next action
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"Error while interacting with group {group_name}: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error sending message to {group_name}: {str(e)}")
        return False

def process_generic_messages(driver, df, message_text, filepath):
    """
    Process and send generic messages to WhatsApp groups.
    """
    results = {
        'success': [],
        'failed': []
    }
    
    # Get unique group names and their corresponding client names
    groups = df[['group_name', 'client_name']] if 'client_name' in df.columns else df[['group_name']]
    groups = groups.drop_duplicates()
    total_groups = len(groups)
    print(f"Processing {total_groups} groups...")
    
    for index, row in groups.iterrows():
        group_name = row['group_name']
        # Get client name if available, otherwise use "Client"
        client_name = row['client_name'] if 'client_name' in row.index else "Client"
        
        try:
            print(f"\nProcessing group {index + 1}/{total_groups}: {group_name}")
            
            # Add test mode prefix if needed
            is_test = "testing" in group_name.lower()
            prefix = "[TEST MODE] " if is_test else ""
            
            # Format message with client name
            formatted_message = f"{prefix}Dear {client_name},\n\n{message_text}"
            
            if is_test:
                formatted_message += "\n\n[THIS IS A TEST MESSAGE - PLEASE IGNORE]"
            
            # Use the existing send_whatsapp_message function which handles line breaks properly
            if send_whatsapp_message(driver, group_name, formatted_message):
                results['success'].append(group_name)
                print(f"Successfully sent message to {group_name}")
            else:
                results['failed'].append({
                    'group': group_name,
                    'error': 'Failed to send message'
                })
                print(f"Failed to send message to {group_name}")
            
        except Exception as e:
            print(f"Failed to send message to {group_name}: {str(e)}")
            results['failed'].append({
                'group': group_name,
                'error': str(e)
            })
            continue
    
    return results

def process_recommendations(driver, df, format_type='simple', uploaded_file_path=None):
    """Process recommendations and send messages to respective groups."""
    results = {
        'success': [],
        'failed': []
    }
    
    try:
        print("\nStarting to process recommendations...")
        print(f"Found {len(df.groupby('group_name'))} groups to process")
        print(f"Using {format_type} format for messages")
        
        # Group the data by group_name
        for group_name, group_data in df.groupby('group_name'):
            try:
                print(f"\nProcessing group: {group_name}")
                print(f"Number of recommendations for this group: {len(group_data)}")
                
                # Format message for this group
                message = format_recommendation_message(group_data, group_name, format_type)
                print("Message formatted successfully")
                
                # Send message
                if send_whatsapp_message(driver, group_name, message):
                    results['success'].append(group_name)
                    print(f"Successfully sent message to {group_name}")
                else:
                    results['failed'].append(group_name)
                    print(f"Failed to send message to {group_name}")
                    
            except Exception as e:
                print(f"Error processing group {group_name}: {str(e)}")
                results['failed'].append(group_name)
        
        print("\nFinished processing all groups")
        print(f"Successful: {len(results['success'])} groups")
        print(f"Failed: {len(results['failed'])} groups")
        
    finally:
        # Clean up data
        print("\nCleaning up data...")
        try:
            # Clear the DataFrame
            df.drop(df.index, inplace=True)
            
            # Remove the uploaded file if path is provided
            if uploaded_file_path:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
                    print(f"Removed uploaded file: {uploaded_file_path}")
            
            print("Data cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
    
    return results 