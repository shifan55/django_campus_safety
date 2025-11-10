(function () {
    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn, { once: true });
        } else {
            fn();
        }
    }

    ready(function () {
        document.querySelectorAll('[data-chat]').forEach(function (chat) {
            const scroller = chat.querySelector('[data-chat-scroll]');
            const list = chat.querySelector('[data-chat-list]');
            if (scroller && list) {
                let userAtBottom = true;

                const isNearBottom = () => {
                    return (scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight) <= 120;
                };

                const scrollToBottom = (behavior = 'auto') => {
                    scroller.scrollTo({ top: scroller.scrollHeight, behavior });
                };

                scrollToBottom('auto');

                scroller.addEventListener('scroll', () => {
                    userAtBottom = isNearBottom();
                });

                const observer = new MutationObserver(() => {
                    if (userAtBottom) {
                        scrollToBottom('smooth');
                    }
                });

                observer.observe(list, { childList: true, subtree: true });

                if (list.children.length > 120 && !chat.querySelector('.chat__virtualization')) {
                    const note = document.createElement('p');
                    note.className = 'chat__virtualization';
                    note.textContent = 'Tip: For lengthy conversations consider enabling virtualization or pagination to improve performance.';
                    scroller.appendChild(note);
                }
            }

            const composer = chat.querySelector('[data-chat-composer]');
            if (composer) {
                const textarea = composer.querySelector('[data-chat-textarea]');
                const parentInput = composer.querySelector('[data-chat-parent-input]');
                const indicator = composer.querySelector('[data-chat-reply-indicator]');
                const indicatorName = indicator ? indicator.querySelector('[data-chat-reply-name]') : null;
                const cancelReply = composer.querySelector('[data-chat-reply-cancel]');
                const attachmentInput = composer.querySelector('[data-chat-attachment]');
                const attachmentTrigger = composer.querySelector('[data-chat-attach-trigger]');
                const attachmentFeedback = composer.querySelector('[data-chat-attachment-feedback]');
                const emojiButton = composer.querySelector('[data-chat-emoji]');

                if (textarea) {
                    const autosize = () => {
                        textarea.style.height = 'auto';
                        textarea.style.height = Math.min(textarea.scrollHeight, 220) + 'px';
                    };
                    textarea.addEventListener('input', autosize);
                    textarea.addEventListener('focus', autosize);
                    autosize();

                    textarea.addEventListener('keydown', (event) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                            event.preventDefault();
                            if (composer.reportValidity()) {
                                composer.requestSubmit();
                            }
                        }
                    });
                }

                if (attachmentTrigger && attachmentInput) {
                    attachmentTrigger.addEventListener('click', (event) => {
                        event.preventDefault();
                        attachmentInput.click();
                    });
                }

                if (attachmentInput && attachmentFeedback) {
                    const defaultFeedback = attachmentFeedback.textContent;
                    attachmentInput.addEventListener('change', () => {
                        if (attachmentInput.files && attachmentInput.files.length) {
                            const file = attachmentInput.files[0];
                            attachmentFeedback.textContent = 'Attached: ' + file.name;
                            attachmentFeedback.classList.add('text-success');
                        } else {
                            attachmentFeedback.textContent = defaultFeedback;
                            attachmentFeedback.classList.remove('text-success');
                        }
                    });
                }

                if (cancelReply) {
                    cancelReply.addEventListener('click', (event) => {
                        event.preventDefault();
                        if (indicator) {
                            indicator.classList.remove('is-active');
                        }
                        if (indicatorName) {
                            indicatorName.textContent = '';
                        }
                        if (parentInput) {
                            parentInput.value = '';
                        }
                    });
                }

                if (emojiButton && textarea) {
                    emojiButton.addEventListener('click', (event) => {
                        event.preventDefault();
                        const emoji = emojiButton.getAttribute('data-chat-emoji-value') || '🙂';
                        const start = textarea.selectionStart || textarea.value.length;
                        const end = textarea.selectionEnd || textarea.value.length;
                        const text = textarea.value;
                        textarea.value = text.slice(0, start) + emoji + text.slice(end);
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                        textarea.focus({ preventScroll: false });
                        const caret = start + emoji.length;
                        textarea.setSelectionRange(caret, caret);
                    });
                }
            }
        });

        document.querySelectorAll('[data-chat-reply]').forEach(function (button) {
            button.addEventListener('click', function () {
                const chat = button.closest('[data-chat]');
                if (!chat) {
                    return;
                }
                const composer = chat.querySelector('[data-chat-composer]');
                if (!composer) {
                    return;
                }
                const parentInput = composer.querySelector('[data-chat-parent-input]');
                const textarea = composer.querySelector('[data-chat-textarea]');
                const indicator = composer.querySelector('[data-chat-reply-indicator]');
                const indicatorName = indicator ? indicator.querySelector('[data-chat-reply-name]') : null;

                if (parentInput) {
                    parentInput.value = button.dataset.parent || '';
                }
                if (indicator) {
                    indicator.classList.add('is-active');
                }
                if (indicatorName) {
                    indicatorName.textContent = button.dataset.author || '';
                }
                if (textarea) {
                    textarea.focus({ preventScroll: false });
                    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
                }
            });
        });

        document.querySelectorAll('[data-suggestion]').forEach(function (chip) {
            chip.addEventListener('click', function () {
                const chat = chip.closest('[data-chat]');
                if (!chat) {
                    return;
                }
                const composer = chat.querySelector('[data-chat-composer]');
                const textarea = composer ? composer.querySelector('[data-chat-textarea]') : null;
                if (!textarea) {
                    return;
                }
                const suggestion = chip.dataset.suggestion || '';
                if (!suggestion) {
                    return;
                }
                const existing = textarea.value.trim();
                textarea.value = existing ? existing + '\n\n' + suggestion : suggestion;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.focus({ preventScroll: false });
            });
        });
    });
})();