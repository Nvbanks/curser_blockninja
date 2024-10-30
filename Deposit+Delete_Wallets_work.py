from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ApplicationBuilder, ContextTypes
import requests
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
import json
import os

# Bot token
TOKEN = "7240071349:AAHiyo_amdbxF-mgrx8lFDamEs-XA_8ss78"

# Global variables
WALLET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wallets.json')
user_wallets = {}

print(f"Using wallet file: {WALLET_FILE}")

def save_wallets():
    try:
        save_data = {}
        for user_id, wallets in user_wallets.items():
            save_data[str(user_id)] = [
                {'name': w['name'], 'public_key': str(w['public_key'])}
                for w in wallets
            ]
        with open(WALLET_FILE, 'w') as f:
            json.dump(save_data, f, indent=4)
        print(f"✅ Wallets saved to {WALLET_FILE}")
        print(f"💾 Saved data: {save_data}")
    except Exception as e:
        print(f"❌ Error saving wallets: {e}")

def load_wallets():
    global user_wallets
    try:
        if os.path.exists(WALLET_FILE):
            with open(WALLET_FILE, 'r') as f:
                data = json.load(f)
            for user_id, wallets in data.items():
                user_wallets[int(user_id)] = [
                    {'name': w['name'], 'public_key': Pubkey.from_string(w['public_key'])}
                    for w in wallets
                ]
            print(f"✅ Loaded wallets from {WALLET_FILE}")
            print(f"💾 Current wallets: {user_wallets}")
        else:
            print("⚠️ No wallet file found, starting fresh")
    except Exception as e:
        print(f"❌ Error loading wallets: {e}")

async def get_sol_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd')
        return response.json()['solana']['usd']
    except:
        return 0

async def get_wallet_balance(public_key):
    try:
        client = Client("https://api.mainnet-beta.solana.com")
        print(f"Checking balance for: {public_key}")
        
        if isinstance(public_key, str):
            public_key = Pubkey.from_string(public_key)
        
        balance_response = client.get_balance(public_key)
        balance_lamports = balance_response.value
        balance_sol = balance_lamports / 1e9
        
        sol_price = await get_sol_price()
        usd_balance = balance_sol * sol_price
        
        return balance_sol, usd_balance
    except Exception as e:
        print(f"Error in get_wallet_balance: {e}")
        return 0, 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏆 Wallet Snipe", callback_data='wallet_snipe')],
        [InlineKeyboardButton("My Wallets 💰", callback_data='my_wallets')],
        [InlineKeyboardButton("Deposit 💵", callback_data='deposit')],
        [InlineKeyboardButton("Positions 📈", callback_data='positions'),
         InlineKeyboardButton("Copy Trading 🤖", callback_data='copy_trading')],
        [InlineKeyboardButton("Referral 🎁", callback_data='referral'),
         InlineKeyboardButton("Settings ⚙️", callback_data='settings')],
        [InlineKeyboardButton("Community 📢", callback_data='community'),
         InlineKeyboardButton("Tutorials 📚", callback_data='tutorials')],
        [InlineKeyboardButton("Refresh 🔄", callback_data='refresh')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to BlockNinja!\nYour wallet is ready to use. Please choose an option:",
        reply_markup=reply_markup
    )

async def create_wallet(update: Update, context):
    try:
        user_id = update.callback_query.from_user.id
        print(f"👤 Creating wallet for user {user_id}")
        
        wallet_name = context.user_data.get('pending_wallet_name', 'Default')
        keypair = Keypair()
        public_key = keypair.pubkey()
        
        if user_id not in user_wallets:
            user_wallets[user_id] = []
            
        user_wallets[user_id].append({
            'name': wallet_name,
            'public_key': public_key
        })
        
        # Save immediately
        save_wallets()
        print(f"💾 Wallet saved for user {user_id}")
        
        # Get the bytes of the secret key
        secret_bytes = bytes(keypair)
        secret_hex = secret_bytes.hex()
        
        wallet_message = (
            f"✅ New wallet '{wallet_name}' created!\n\n"
            f"Public Key:\n`{public_key}`\n\n"
            f"Private Key:\n`{secret_hex}`\n\n"
            "⚠️ Save your private key! It won't be shown again."
        )
        
        keyboard = [[InlineKeyboardButton("Back to My Wallets ⬅️", callback_data='back_to_wallets')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            wallet_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Error in create_wallet: {e}")
        await update.callback_query.message.edit_text("Error creating wallet. Please try again.")

async def show_wallets_menu(update: Update, context):
    user_id = update.callback_query.from_user.id
    wallets = user_wallets.get(user_id, [])
    
    keyboard = []
    for i, wallet in enumerate(wallets):
        keyboard.append([InlineKeyboardButton(f"{wallet['name']} 👛", callback_data=f'edit_wallet_{i}')])
    
    keyboard.append([InlineKeyboardButton("Create Wallet 🔑", callback_data='create_wallet')])
    keyboard.append([InlineKeyboardButton("Back to Main Menu ⬅️", callback_data='back_to_main')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text("Your Wallets:", reply_markup=reply_markup)

async def edit_wallet_menu(update: Update, context, wallet_idx):
    user_id = update.callback_query.from_user.id
    wallets = user_wallets.get(user_id, [])
    wallet = wallets[wallet_idx]
    
    sol_balance, usd_balance = await get_wallet_balance(wallet['public_key'])
    
    address_message = (
        f"Wallet Address: `{wallet['public_key']}`\n"
        f"Balance: {sol_balance:.9f} SOL (${usd_balance:.2f})"
    )
    
    keyboard = [
        [InlineKeyboardButton("Delete Wallet ❌", callback_data=f'confirm_delete_wallet_{wallet_idx}')],
        [InlineKeyboardButton("Open in Web 🌐", callback_data=f'open_web_{wallet_idx}')],
        [InlineKeyboardButton("Deposit 💵", callback_data=f'deposit_wallet_{wallet_idx}'),
         InlineKeyboardButton("Withdraw 💸", callback_data=f'withdraw_wallet_{wallet_idx}')],
        [InlineKeyboardButton("Back to My Wallets ⬅️", callback_data='back_to_wallets')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        f"{address_message}\n\nEdit {wallet['name']} Wallet:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def confirm_delete_wallet(update: Update, context, wallet_idx):
    user_id = update.callback_query.from_user.id
    wallets = user_wallets.get(user_id, [])
    wallet = wallets[wallet_idx]
    
    keyboard = [
        [InlineKeyboardButton("Yes, Delete ✅", callback_data=f'delete_wallet_{wallet_idx}'),
         InlineKeyboardButton("No, Keep ❌", callback_data=f'edit_wallet_{wallet_idx}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"Are you sure you want to delete the wallet '{wallet['name']}'?",
        reply_markup=reply_markup
    )

async def delete_wallet(update: Update, context, wallet_idx):
    user_id = update.callback_query.from_user.id
    if user_id in user_wallets and wallet_idx < len(user_wallets[user_id]):
        wallet_name = user_wallets[user_id][wallet_idx]['name']
        del user_wallets[user_id][wallet_idx]
        save_wallets()
        await show_wallets_menu(update, context)

async def deposit_wallet(update: Update, context, wallet_idx):
    user_id = update.callback_query.from_user.id
    wallets = user_wallets.get(user_id, [])
    wallet = wallets[wallet_idx]
    
    deposit_message = (
        f"Send SOL to this address:\n\n"
        f"`{wallet['public_key']}`\n\n"
        f"Network: Solana (SOL)\n"
        f"_Only send SOL to this address!_"
    )
    
    keyboard = [[InlineKeyboardButton("Back to Wallet ⬅️", callback_data=f'edit_wallet_{wallet_idx}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        deposit_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    print(f"Button pressed: {query.data}")
    
    if query.data == 'my_wallets':
        await show_wallets_menu(update, context)
    elif query.data == 'create_wallet':
        await create_wallet(update, context)
    elif query.data.startswith('edit_wallet_'):
        wallet_idx = int(query.data.split('_')[2])
        await edit_wallet_menu(update, context, wallet_idx)
    elif query.data == 'back_to_wallets':
        await show_wallets_menu(update, context)
    elif query.data == 'back_to_main':
        keyboard = [
            [InlineKeyboardButton("🏆 Wallet Snipe", callback_data='wallet_snipe')],
            [InlineKeyboardButton("My Wallets 💰", callback_data='my_wallets')],
            [InlineKeyboardButton("Deposit 💵", callback_data='deposit')],
            [InlineKeyboardButton("Positions 📈", callback_data='positions'),
             InlineKeyboardButton("Copy Trading 🤖", callback_data='copy_trading')],
            [InlineKeyboardButton("Referral 🎁", callback_data='referral'),
             InlineKeyboardButton("Settings ⚙️", callback_data='settings')],
            [InlineKeyboardButton("Community 📢", callback_data='community'),
             InlineKeyboardButton("Tutorials 📚", callback_data='tutorials')],
            [InlineKeyboardButton("Refresh 🔄", callback_data='refresh')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "Welcome to BlockNinja!\nYour wallet is ready to use. Please choose an option:",
            reply_markup=reply_markup
        )
    elif query.data.startswith('deposit_wallet_'):
        wallet_idx = int(query.data.split('_')[2])
        await deposit_wallet(update, context, wallet_idx)
    elif query.data.startswith('open_web_'):
        wallet_idx = int(query.data.split('_')[2])
        wallets = user_wallets.get(query.from_user.id, [])
        wallet = wallets[wallet_idx]
        explorer_url = f"https://solscan.io/account/{wallet['public_key']}"
        keyboard = [[InlineKeyboardButton("Back ⬅️", callback_data=f'edit_wallet_{wallet_idx}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"View wallet on Solscan:\n{explorer_url}", reply_markup=reply_markup)
    elif query.data.startswith('confirm_delete_wallet_'):
        wallet_idx = int(query.data.split('_')[3])
        await confirm_delete_wallet(update, context, wallet_idx)
    elif query.data.startswith('delete_wallet_'):
        wallet_idx = int(query.data.split('_')[2])
        await delete_wallet(update, context, wallet_idx)

def main():
    print("🚀 Starting bot...")
    
    # Load existing wallets
    print("📂 Loading wallets...")
    load_wallets()
    print(f"💾 Initial wallets: {user_wallets}")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot initialized")
    print("🔄 Starting polling...")
    
    application.run_polling()

if __name__ == '__main__':
    main()