import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { RagDocument } from '../models/document';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private documentsSubject = new BehaviorSubject<RagDocument[]>([]);
  documents$: Observable<RagDocument[]> = this.documentsSubject.asObservable();

  private apiUrl = 'http://localhost:8000/api/documents';

  constructor(private http: HttpClient) { }

  loadDocuments(): void {
    this.http.get<RagDocument[]>(this.apiUrl).subscribe({
      next: (docs) => this.documentsSubject.next(docs.map(d => ({ ...d, selected: true }))),
      error: (err) => console.error('Erreur chargement documents', err)
    });
  }

  uploadDocument(file: File): void {
    const tempId = crypto.randomUUID();
    const tempDoc: RagDocument = {
      id: tempId,
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date(),
      status: 'uploading',
      selected: true
    };
    this.documentsSubject.next([...this.documentsSubject.value, tempDoc]);

    const formData = new FormData();
    formData.append('file', file);

    this.http.post<RagDocument>(this.apiUrl, formData).subscribe({
      next: (saved) => this.replace(tempId, { ...saved, selected: true, status: 'ready' }),
      error: () => this.replace(tempId, { ...tempDoc, status: 'error' })
    });
  }

  deleteDocument(id: string): void {
    this.http.delete(`${this.apiUrl}/${id}`).subscribe({
      next: () => this.documentsSubject.next(this.documentsSubject.value.filter(d => d.id !== id)),
      error: (err) => console.error('Erreur suppression document', err)
    });
  }

  toggleSelection(id: string): void {
    this.documentsSubject.next(
      this.documentsSubject.value.map(d => d.id === id ? { ...d, selected: !d.selected } : d)
    );
  }

  getSelectedDocumentIds(): string[] {
    return this.documentsSubject.value.filter(d => d.selected).map(d => d.id);
  }

  private replace(id: string, updated: RagDocument): void {
    this.documentsSubject.next(this.documentsSubject.value.map(d => d.id === id ? updated : d));
  }
}