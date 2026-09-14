import { Component } from '@angular/core';
import { ChatComponent } from './components/chat/chat';
import { DocumentPanelComponent } from './components/document-panel/document-panel';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ChatComponent, DocumentPanelComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent { }