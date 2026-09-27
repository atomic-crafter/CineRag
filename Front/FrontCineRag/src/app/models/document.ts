export type DocumentStatus = 'uploading' | 'ready' | 'error';

export interface RagDocument {
    id: string;
    name: string;
    size: number;      // octets
    type: string;       // mime type
    uploadedAt: Date;
    status: DocumentStatus;
    selected: boolean;  // utilisé ou non pour la prochaine question
}