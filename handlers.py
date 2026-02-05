    # ============ ДОБАВЛЕНИЕ ДОЛГА (НОВАЯ ЛОГИКА) ============
    
    async def start_debt_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс добавления долга"""
        user = update.effective_user
        
        chat_id = context.user_data.get('expense_chat_id')
        if not chat_id:
            chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            text = "❌ Активная поездка не найдена"
            if update.callback_query:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END
        
        trip = Database.get_trip(chat_id)
        if not trip:
            text = "❌ Поездка не найдена"
            if update.callback_query:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END
        
        context.user_data['expense_chat_id'] = chat_id
        context.user_data['expense_data'] = {}
        
        participants = Database.get_participants(chat_id)
        participants_text = ", ".join([f"@{p['username']}" if p.get('username') else p['first_name'] for p in participants])
        
        text = (
            f"➕ *Новый долг* ({trip['currency']})\n\n"
            "🎯 *Как это работает:*\n"
            "1. Вы пишете сумму и участников через @\n"
            "2. Бот делит сумму на всех участников\n"
            "3. Плательщик не должен сам себе\n"
            "4. Все получают уведомления\n\n"
            "📝 *Формат:*\n"
            "`Сумма @участник1 @участник2 описание`\n\n"
            "💡 *Пример:*\n"
            "`2000 @саша @никита @катя такси в аэропорт`\n\n"
            f"👥 Доступные участники:\n{participants_text}\n\n"
            "✍️ Напишите ваш долг:"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
        
        return EXPENSE_AMOUNT
    
    async def expense_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Новая логика: парсим всё из одного сообщения
        Формат: "2000 @саша @никита @катя такси в аэропорт"
        """
        text = update.message.text
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        # Парсим сообщение
        parts = text.split()
        
        # Первое слово - сумма
        is_valid, amount = Utils.validate_amount(parts[0])
        if not is_valid:
            await update.message.reply_text(
                f"❌ {amount}\n\n"
                "Начните сообщение с суммы, например:\n"
                "`2000 @саша @никита такси`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
            return EXPENSE_AMOUNT
        
        # Извлекаем участников
        mentioned_ids = Utils.parse_participants_from_text(text, participants)
        
        if len(mentioned_ids) < 2:
            await update.message.reply_text(
                "❌ Укажите минимум 2 участников через @ или по имени\n\n"
                "Пример: `2000 @никита @саша такси`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
            return EXPENSE_AMOUNT
        
        # Описание - всё что после участников
        description_parts = []
        for part in parts[1:]:
            if not part.startswith('@') and not any(p['first_name'].lower() in part.lower() for p in participants):
                description_parts.append(part)
        
        description = ' '.join(description_parts) if description_parts else "Общий расход"
        
        # Спрашиваем кто заплатил
        context.user_data['expense_data'] = {
            'amount': amount,
            'participants': mentioned_ids,
            'description': description
        }
        
        # Показываем кнопки только с участниками долга
        mentioned_participants = [p for p in participants if p['user_id'] in mentioned_ids]
        
        text = (
            f"✅ Сумма: *{amount}*\n"
            f"👥 Участники: {len(mentioned_ids)}\n"
            f"📝 Описание: {description}\n\n"
            "💳 Кто заплатил?"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_payer_selection(mentioned_participants)
        )
        
        return EXPENSE_PAYER
    
    async def expense_payer_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор плательщика"""
        query = update.callback_query
        await query.answer()
        
        payer_id = int(query.data.split('_')[1])
        context.user_data['expense_data']['payer_id'] = payer_id
        
        # Выбор категории
        text = "📁 Выберите категорию (опционально):"
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.expense_category()
        )
        
        return EXPENSE_CATEGORY
    
    async def expense_category_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор категории"""
        query = update.callback_query
        await query.answer()
        
        category = query.data.split('_')[1]
        context.user_data['expense_data']['category'] = category
        
        return await self.expense_confirm_and_save(update, context)
    
    async def expense_category_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропустить категорию"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['expense_data']['category'] = '💸'
        
        return await self.expense_confirm_and_save(update, context)
    
    async def expense_confirm_and_save(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение и сохранение"""
        query = update.callback_query
        
        expense_data = context.user_data['expense_data']
        chat_id = context.user_data['expense_chat_id']
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        amount = expense_data['amount']
        payer_id = expense_data['payer_id']
        debt_participants = expense_data['participants']
        description = expense_data['description']
        category = expense_data.get('category', '💸')
        
        payer_name = Utils.get_participant_name(payer_id, participants)
        
        # Создаем долг
        debt_result = Database.create_debt(
            chat_id=chat_id,
            amount=amount,
            payer_id=payer_id,
            participants=debt_participants,
            description=description,
            category=category
        )
        
        if not debt_result:
            await query.edit_message_text("❌ Ошибка создания долга")
            return ConversationHandler.END
        
        # Считаем кто сколько должен
        debtors = [p for p in debt_participants if p != payer_id]
        amount_per_person = amount / len(debtors)
        
        # Уведомление в ЛС создателю
        await query.edit_message_text(
            f"✅ Долг добавлен!\n\n"
            f"{category} *{description}*\n"
            f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
            f"👤 Заплатил: {payer_name}\n"
            f"💳 На человека: {Utils.format_amount(amount_per_person, trip['currency'])}\n\n"
            f"Участников: {len(debt_participants)}\n"
            f"Должников: {len(debtors)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Публикуем в группу
        try:
            debtor_names = [Utils.get_participant_name(d, participants) for d in debtors]
            
            group_text = (
                f"💸 *Новый долг*\n\n"
                f"{category} *{description}*\n"
                f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
                f"👤 Заплатил: {payer_name}\n"
                f"💳 Должны по: {Utils.format_amount(amount_per_person, trip['currency'])}\n\n"
                f"👥 Должники: {', '.join(debtor_names)}"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=group_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Обновляем сводку
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=summary_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.summary_actions(self.bot_username, chat_id)
            )
            
        except Exception as e:
            logger.error(f"Error sending to group: {e}")
        
        # Отправляем пуши всем участникам
        await self.send_debt_notifications(context, chat_id, debt_result, participants, trip)
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def send_debt_notifications(self, context: ContextTypes.DEFAULT_TYPE, 
                                      chat_id: int, debt_result: dict, 
                                      participants: list, trip: dict):
        """Отправить пуш-уведомления о новом долге"""
        group_data = debt_result['group_data']
        individual_debts = debt_result['debts']
        
        payer_id = group_data['payer_id']
        payer_name = Utils.get_participant_name(payer_id, participants)
        description = group_data['description']
        category = group_data.get('category', '💸')
        
        # Отправляем должникам
        for debt in individual_debts:
            debtor_id = debt['debtor_id']
            amount = debt['amount']
            
            settings = Database.get_user_settings(debtor_id)
            if settings.get('notification_type') == 'off':
                continue
            
            try:
                text = (
                    f"🔔 *Новый долг в \"{trip['name']}\"*\n\n"
                    f"{category} {description}\n"
                    f"💰 Вы должны {payer_name}: *{Utils.format_amount(amount, trip['currency'])}*\n\n"
                    f"Нажмите /start чтобы посмотреть все долги"
                )
                
                await context.bot.send_message(
                    chat_id=debtor_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {debtor_id}: {e}")
        
        # Уведомление плательщику
        try:
            total_owed = sum(d['amount'] for d in individual_debts)
            text = (
                f"✅ *Долг создан в \"{trip['name']}\"*\n\n"
                f"{category} {description}\n"
                f"💰 Вам должны: *{Utils.format_amount(total_owed, trip['currency'])}*\n"
                f"👥 Должников: {len(individual_debts)}"
            )
            
            await context.bot.send_message(
                chat_id=payer_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send notification to payer {payer_id}: {e}")
    
    async def expense_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена добавления долга"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Добавление долга отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # ============ ВОЗВРАТ ДОЛГА ============
    
    async def show_debt_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали конкретного долга с кнопкой оплаты"""
        query = update.callback_query
        await query.answer()
        
        debt_id = query.data.split('_')[2]
        
        # Получаем долг из БД
        debt_doc = db.collection('debts').document(debt_id).get()
        if not debt_doc.exists:
            await query.edit_message_text("❌ Долг не найден")
            return
        
        debt = debt_doc.to_dict()
        chat_id = debt['chat_id']
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        # Получаем инфо о группе долга
        debt_group = db.collection('debt_groups').document(debt['debt_group_id']).get()
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
        else:
            description = "Долг"
            category = "💸"
        
        creditor_name = Utils.get_participant_name(debt['creditor_id'], participants)
        amount = Utils.format_amount(debt['amount'], trip['currency'])
        
        text = (
            f"{category} *{description}*\n\n"
            f"💰 Сумма: *{amount}*\n"
            f"👤 Должен: {creditor_name}\n"
            f"📅 Создан: {debt['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Вернули долг?"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debt_pay_button(debt_id)
        )
    
    async def pay_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить долг как возвращенный"""
        query = update.callback_query
        await query.answer("✅ Долг отмечен как возвращенный!")
        
        debt_id = query.data.split('_')[2]
        
        # Отмечаем долг как оплаченный
        debt_data = Database.mark_debt_paid(debt_id)
        
        if not debt_data:
            await query.edit_message_text("❌ Ошибка при обновлении долга")
            return
        
        chat_id = debt_data['chat_id']
        creditor_id = debt_data['creditor_id']
        debtor_id = debt_data['debtor_id']
        amount = debt_data['amount']
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        debtor_name = Utils.get_participant_name(debtor_id, participants)
        creditor_name = Utils.get_participant_name(creditor_id, participants)
        
        # Получаем инфо о долге
        debt_group = db.collection('debt_groups').document(debt_data['debt_group_id']).get()
        description = "Долг"
        category = "💸"
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
        
        # Уведомление должнику
        await query.edit_message_text(
            f"✅ *Долг возвращен!*\n\n"
            f"{category} {description}\n"
            f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
            f"👤 Кредитор: {creditor_name}\n\n"
            f"Спасибо за честность! 🎉",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Пуш кредитору
        try:
            text = (
                f"💰 *Долг возвращен!*\n\n"
                f"👤 {debtor_name} вернул вам долг:\n"
                f"{category} {description}\n"
                f"💵 Сумма: *{Utils.format_amount(amount, trip['currency'])}*\n\n"
                f"Поездка: {trip['name']}"
            )
            
            await context.bot.send_message(
                chat_id=creditor_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to notify creditor: {e}")
        
        # Обновляем сводку в группе
        try:
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {debtor_name} вернул долг {creditor_name}\n\n{summary_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to update group: {e}")
    
    # ============ CALLBACK HANDLERS ============
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик callback'ов"""
        query = update.callback_query
        data = query.data
        
        # Навигация в ЛС
        if data == "dm_back":
            return await self.show_dm_cabinet(update, context)
        
        elif data == "dm_debts":
            return await self.show_debts_dm(update, context)
        
        elif data == "dm_history":
            return await self.show_history_dm(update, context)
        
        elif data == "dm_notifications":
            return await self.show_notifications_settings(update, context)
        
        elif data == "debts_i_owe":
            return await self.show_i_owe(update, context)
        
        elif data == "debts_owe_me":
            return await self.show_owe_me(update, context)
        
        elif data == "debts_refresh":
            return await self.show_debts_dm(update, context)
        
        elif data.startswith("show_debt_"):
            return await self.show_debt_detail(update, context)
        
        elif data.startswith("pay_debt_"):
            return await self.pay_debt(update, context)
        
        # Групповой чат
        elif data == "add_expense":
            return await self.expense_command(update, context)
        
        elif data == "show_summary":
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                summary_text = Utils.format_summary(chat.id)
                await query.edit_message_text(
                    summary_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
                )
            await query.answer()
        
        elif data == "show_participants":
            await query.answer()
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                participants = Database.get_participants(chat.id)
                text = f"👥 *Участники* ({len(participants)}):\n\n"
                for p in participants:
                    text += f"• {p['first_name']}"
                    if p.get('username'):
                        text += f" (@{p['username']})"
                    text += "\n"
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
                    ]])
                )
        
        elif data == "back_to_menu":
            await query.answer()
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                await query.edit_message_text(
                    f"🎯 *{trip['name']}* — управление:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=Keyboards.main_group_menu()
                )
        
        else:
            await query.answer()
