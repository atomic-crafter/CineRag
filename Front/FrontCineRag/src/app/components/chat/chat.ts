import { Component, ElementRef, OnInit, ViewChild, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat';
import { DocumentService } from '../../services/document';
import { MessageBubbleComponent } from '../message-bubble/message-bubble';
import { ChatMessage } from '../../models/message';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MessageBubbleComponent],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollAnchor') private scrollAnchor!: ElementRef<HTMLDivElement>;

  messages: ChatMessage[] = [];
  draft = '';

  constructor(private chatService: ChatService, private documentService: DocumentService) { }

  ngOnInit(): void {
    this.chatService.messages$.subscribe(msgs => this.messages = msgs);
  }

  ngAfterViewChecked(): void {
    this.scrollAnchor?.nativeElement.scrollIntoView({ behavior: 'smooth' });
  }

  send(): void {
    const content = this.draft.trim();
    if (!content) return;
    const selectedIds = this.documentService.getSelectedDocumentIds();
    this.chatService.sendMessage(content, selectedIds);
    this.draft = '';
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }
}