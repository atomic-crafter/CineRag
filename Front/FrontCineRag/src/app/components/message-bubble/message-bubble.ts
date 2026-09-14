import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatMessage } from '../../models/message';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './message-bubble.html',
  styleUrl: './message-bubble.scss'
})
export class MessageBubbleComponent {
  @Input({ required: true }) message!: ChatMessage;
}