/**
 * CodePilot VSCode Extension
 * Main extension file
 */

import * as vscode from 'vscode';
import axios from 'axios';

let statusBarItem: vscode.StatusBarItem;

interface CompletionResponse {
    completion: string;
    tokens_generated: number;
    finish_reason: string;
}

interface Config {
    apiEndpoint: string;
    enableAutoComplete: boolean;
    maxTokens: number;
    temperature: number;
    debounceMs: number;
}

function getConfig(): Config {
    const config = vscode.workspace.getConfiguration('codepilot');
    return {
        apiEndpoint: config.get('apiEndpoint', 'http://localhost:8000'),
        enableAutoComplete: config.get('enableAutoComplete', true),
        maxTokens: config.get('maxTokens', 150),
        temperature: config.get('temperature', 0.2),
        debounceMs: config.get('debounceMs', 300)
    };
}

async function callCodePilotAPI(
    endpoint: string,
    data: any
): Promise<any> {
    const config = getConfig();
    const url = `${config.apiEndpoint}${endpoint}`;
    
    try {
        const response = await axios.post(url, data, {
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return response.data;
    } catch (error: any) {
        if (error.code === 'ECONNREFUSED') {
            throw new Error('Cannot connect to CodePilot server. Make sure the server is running.');
        }
        throw error;
    }
}

/**
 * Code completion provider
 */
class CodePilotCompletionProvider implements vscode.InlineCompletionItemProvider {
    private debounceTimer?: NodeJS.Timeout;
    
    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList> {
        const config = getConfig();
        
        if (!config.enableAutoComplete) {
            return [];
        }
        
        // Get text before cursor
        const textBeforeCursor = document.getText(
            new vscode.Range(new vscode.Position(0, 0), position)
        );
        
        // Don't trigger on empty lines or very short input
        if (textBeforeCursor.trim().length < 10) {
            return [];
        }
        
        try {
            // Update status bar
            statusBarItem.text = "$(loading~spin) CodePilot";
            statusBarItem.show();
            
            // Call API
            const response: CompletionResponse = await callCodePilotAPI('/complete', {
                prompt: textBeforeCursor,
                max_tokens: config.maxTokens,
                temperature: config.temperature
            });
            
            // Update status bar
            statusBarItem.text = "$(check) CodePilot";
            
            // Create completion item
            const completionItem = new vscode.InlineCompletionItem(
                response.completion,
                new vscode.Range(position, position)
            );
            
            return [completionItem];
            
        } catch (error: any) {
            console.error('CodePilot error:', error);
            statusBarItem.text = "$(error) CodePilot";
            return [];
        }
    }
}

/**
 * Explain selected code
 */
async function explainCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    
    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);
    
    if (!selectedText) {
        vscode.window.showErrorMessage('Please select code to explain');
        return;
    }
    
    try {
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "CodePilot is explaining your code...",
            cancellable: false
        }, async () => {
            const response = await callCodePilotAPI('/explain', {
                code: selectedText,
                language: editor.document.languageId
            });
            
            // Show explanation in new panel
            const panel = vscode.window.createWebviewPanel(
                'codepilotExplanation',
                'Code Explanation',
                vscode.ViewColumn.Beside,
                {}
            );
            
            panel.webview.html = getExplanationHTML(selectedText, response.explanation);
        });
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`CodePilot error: ${error.message}`);
    }
}

/**
 * Detect bugs in selected code
 */
async function detectBugs() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    
    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);
    
    if (!selectedText) {
        vscode.window.showErrorMessage('Please select code to analyze');
        return;
    }
    
    try {
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "CodePilot is analyzing code for bugs...",
            cancellable: false
        }, async () => {
            const response = await callCodePilotAPI('/detect-bugs', {
                code: selectedText,
                check_iso26262: true
            });
            
            // Show analysis in new panel
            const panel = vscode.window.createWebviewPanel(
                'codepilotBugAnalysis',
                'Bug Analysis',
                vscode.ViewColumn.Beside,
                {}
            );
            
            panel.webview.html = getBugAnalysisHTML(selectedText, response.analysis);
        });
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`CodePilot error: ${error.message}`);
    }
}

/**
 * Generate unit tests for selected function
 */
async function generateTests() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    
    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);
    
    if (!selectedText) {
        vscode.window.showErrorMessage('Please select a function to generate tests');
        return;
    }
    
    try {
        const framework = await vscode.window.showQuickPick(
            ['unity', 'gtest', 'cppunit'],
            { placeHolder: 'Select test framework' }
        );
        
        if (!framework) {
            return;
        }
        
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "CodePilot is generating unit tests...",
            cancellable: false
        }, async () => {
            const response = await callCodePilotAPI('/generate-tests', {
                function_code: selectedText,
                test_framework: framework
            });
            
            // Create new document with tests
            const doc = await vscode.workspace.openTextDocument({
                content: response.tests,
                language: 'c'
            });
            
            await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
        });
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`CodePilot error: ${error.message}`);
    }
}

function getExplanationHTML(code: string, explanation: string): string {
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { 
                    font-family: var(--vscode-font-family);
                    padding: 20px;
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                }
                pre {
                    background-color: var(--vscode-textCodeBlock-background);
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }
                .explanation {
                    margin-top: 20px;
                    line-height: 1.6;
                }
                h2 {
                    color: var(--vscode-textLink-foreground);
                }
            </style>
        </head>
        <body>
            <h2>Code</h2>
            <pre><code>${escapeHtml(code)}</code></pre>
            
            <h2>Explanation</h2>
            <div class="explanation">
                ${escapeHtml(explanation).replace(/\n/g, '<br>')}
            </div>
        </body>
        </html>
    `;
}

function getBugAnalysisHTML(code: string, analysis: string): string {
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { 
                    font-family: var(--vscode-font-family);
                    padding: 20px;
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                }
                pre {
                    background-color: var(--vscode-textCodeBlock-background);
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }
                .analysis {
                    margin-top: 20px;
                    line-height: 1.6;
                }
                .warning {
                    color: var(--vscode-editorWarning-foreground);
                }
                h2 {
                    color: var(--vscode-textLink-foreground);
                }
            </style>
        </head>
        <body>
            <h2>Code Under Analysis</h2>
            <pre><code>${escapeHtml(code)}</code></pre>
            
            <h2>Bug Analysis</h2>
            <div class="analysis">
                ${escapeHtml(analysis).replace(/\n/g, '<br>')}
            </div>
        </body>
        </html>
    `;
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export function activate(context: vscode.ExtensionContext) {
    console.log('CodePilot extension activated');
    
    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = "$(sparkle) CodePilot";
    statusBarItem.tooltip = "CodePilot - Automotive Code Assistant";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    
    // Register inline completion provider
    const completionProvider = new CodePilotCompletionProvider();
    const providerDisposable = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**/*.{c,cpp,h,hpp}' },
        completionProvider
    );
    context.subscriptions.push(providerDisposable);
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codepilot.explain', explainCode),
        vscode.commands.registerCommand('codepilot.detectBugs', detectBugs),
        vscode.commands.registerCommand('codepilot.generateTests', generateTests)
    );
    
    // Show welcome message
    vscode.window.showInformationMessage('CodePilot activated! Start typing in C/C++ files.');
}

export function deactivate() {
    console.log('CodePilot extension deactivated');
}
