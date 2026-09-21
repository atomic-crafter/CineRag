import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { ChatMessage } from '../models/message';


interface ChatResponse {
    answer: string;
    sources: string[];
}

@Injectable({ providedIn: 'root' })
export class ChatService {
    private messagesSubject = new BehaviorSubject<ChatMessage[]>([]);
    messages$: Observable<ChatMessage[]> = this.messagesSubject.asObservable();

    private apiUrl = '/api/chat';

    constructor(private http: HttpClient) { }

    sendMessage(content: string, selectedDocumentIds: string[]): void {
        const userMessage: ChatMessage = {
            id: crypto.randomUUID(), role: 'user', content, timestamp: new Date()
        };
        const loadingMessage: ChatMessage = {
            id: crypto.randomUUID(), role: 'assistant', content: '', timestamp: new Date(), isLoading: true
        };

        this.messagesSubject.next([...this.messagesSubject.value, userMessage, loadingMessage]);

        this.http.post<ChatResponse>(this.apiUrl, {
            question: content,
            documentIds: selectedDocumentIds
        }).subscribe({
            next: (res) => this.replace(loadingMessage.id, {
                id: loadingMessage.id, role: 'assistant', content: res.answer,
                timestamp: new Date(), sources: res.sources
            }),
            error: () => this.replace(loadingMessage.id, {
                id: loadingMessage.id, role: 'assistant',
                content: "Une erreur est survenue lors de la génération de la réponse.",
                timestamp: new Date()
            })
        });
    }

    private replace(id: string, updated: ChatMessage): void {
        this.messagesSubject.next(this.messagesSubject.value.map(m => m.id === id ? updated : m));
    }
}