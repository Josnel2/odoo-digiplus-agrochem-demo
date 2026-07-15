/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


export class DigiplusAiChat extends Component {
    static template = "digiplus_ai_assistant.AiChat";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.inputRef = useRef("messageInput");
        this.messagesRef = useRef("messages");
        this.state = useState({
            sessionId: false,
            messages: [],
            input: "",
            loading: true,
            sending: false,
        });
        onWillStart(async () => {
            this.state.sessionId = await this.orm.call(
                "ai.chat.session",
                "get_or_create_session",
                []
            );
            await this.loadMessages();
            this.state.loading = false;
        });
        onMounted(() => {
            this.focusInput();
            this.scrollToBottom();
        });
    }

    async loadMessages() {
        this.state.messages = await this.orm.searchRead(
            "ai.chat.message",
            [["session_id", "=", this.state.sessionId]],
            ["role", "content", "create_date", "draft_id"],
            { order: "id asc" }
        );
    }

    async sendMessage() {
        const content = this.state.input.trim();
        if (!content || this.state.sending) {
            return;
        }
        this.state.sending = true;
        this.state.input = "";
        this.state.messages.push({
            id: `pending-${Date.now()}`,
            role: "user",
            content,
            draft_id: false,
        });
        this.scrollToBottom();
        try {
            await this.orm.call(
                "ai.chat.session",
                "send_message",
                [[this.state.sessionId], content]
            );
            await this.loadMessages();
        } catch (error) {
            this.state.input = content;
            await this.loadMessages();
            this.notification.add(
                error.data?.message || error.message || "Le service IA est indisponible.",
                { type: "danger", title: "Assistant IA" }
            );
        } finally {
            this.state.sending = false;
            this.focusInput();
            this.scrollToBottom();
        }
    }

    async newConversation() {
        if (this.state.sending) {
            return;
        }
        this.state.loading = true;
        this.state.sessionId = await this.orm.call("ai.chat.session", "new_session", []);
        await this.loadMessages();
        this.state.loading = false;
        this.focusInput();
        this.scrollToBottom();
    }

    onKeydown(event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    openDraft(message) {
        const draftId = Array.isArray(message.draft_id)
            ? message.draft_id[0]
            : message.draft_id;
        if (draftId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Brouillon IA",
                res_model: "ai.project.draft",
                res_id: draftId,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    focusInput() {
        this.inputRef.el?.focus();
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            const element = this.messagesRef.el;
            if (element) {
                element.scrollTop = element.scrollHeight;
            }
        });
    }
}

registry.category("actions").add("digiplus_ai_chat", DigiplusAiChat);
