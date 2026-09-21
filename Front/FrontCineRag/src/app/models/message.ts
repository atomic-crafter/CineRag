export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: Date;
    sources?: string[];   // noms des documents utilisés pour la réponse
    isLoading?: boolean;  // affiche les "..." pendant la génération
}