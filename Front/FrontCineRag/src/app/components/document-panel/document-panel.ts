import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentService } from '../../services/document';
import { RagDocument } from '../../models/document';

@Component({
  selector: 'app-document-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './document-panel.html',
  styleUrl: './document-panel.scss'
})
export class DocumentPanelComponent implements OnInit {
  documents: RagDocument[] = [];
  isDragging = false;

  constructor(private documentService: DocumentService) { }

  ngOnInit(): void {
    this.documentService.documents$.subscribe(docs => this.documents = docs);
    this.documentService.loadDocuments();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      Array.from(input.files).forEach(file => this.documentService.uploadDocument(file));
      input.value = '';
    }
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    if (event.dataTransfer?.files) {
      Array.from(event.dataTransfer.files).forEach(file => this.documentService.uploadDocument(file));
    }
  }

  onDragOver(event: DragEvent): void { event.preventDefault(); this.isDragging = true; }
  onDragLeave(): void { this.isDragging = false; }

  toggle(doc: RagDocument): void { this.documentService.toggleSelection(doc.id); }

  remove(doc: RagDocument, event: MouseEvent): void {
    event.stopPropagation();
    this.documentService.deleteDocument(doc.id);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }
}