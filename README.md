# WhatsApp Automation Tool

A powerful WhatsApp automation tool for sending personalized messages and stock recommendations to multiple groups.

## Features

- Send personalized messages to multiple WhatsApp groups
- Support for stock recommendations with BUY/SELL signals
- Client name personalization
- Excel file upload for group management
- Secure login system
- Easy-to-use web interface

## Prerequisites

- Python 3.8 or higher
- Chrome browser
- ChromeDriver
- Flask

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python init_db.py
```

5. Start the application:
```bash
python app.py
```

## Usage

1. Access the application at `http://localhost:8080`
2. Log in with your credentials
3. Upload your Excel file with group information
4. Choose between generic message or stock recommendations
5. Send your messages!

## Excel File Format

### For Generic Messages:
- Required columns: `group_name`
- Optional columns: `client_name`

### For Stock Recommendations:
- Required columns: `group_name`, `company_name`, `action`, `target`, `stop_loss`
- Optional columns: `client_name`

## Security

- Login required for access
- Secure password storage
- Session management

## Contributing

Feel free to submit issues and enhancement requests!

## Architecture Diagram
<img width="1020" alt="Screenshot 2025-05-17 at 11 56 42" src="https://github.com/user-attachments/assets/1249ef7c-f915-488a-bcc7-0fc27c03c559" />


## Support

For support, please contact me rushichinna007@gmail.com
