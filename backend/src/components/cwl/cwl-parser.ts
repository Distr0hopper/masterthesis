import { ParameterDirection } from "../enums";
import * as yaml from 'js-yaml';
import {ParameterDto} from "../dto/parameter.dto";

export class CwlParser {
    static generateInputsYaml(parameters: Partial<ParameterDto>[], name: string, version: number): string {
        const lines: string[] = [
            `# CWL inputs for ${name} v${version}`,
            `# Usage: cwltool ${name}-v${version}.cwl inputs.yaml`,
        ];
        for (const p of parameters) {
            if (!p.name) continue;
            const type = (p.cwlType ?? 'string').toLowerCase();
            lines.push(...this.formatInput(p.name, type, p.defaultValue ?? null));
        }
        return lines.join('\n') + '\n';
    }

    private static formatInput(name: string, type: string, defaultValue: string | null): string[] {
        if (type === 'file') return [`${name}:`, `  class: File`, `  path: /path/to/input`];
        if (type === 'directory') return [`${name}:`, `  class: Directory`, `  location: /path/to/dir`];
        if (type === 'double' || type === 'float') {
            const num = defaultValue !== null ? parseFloat(defaultValue) : 0;
            return [`${name}: ${Number.isInteger(num) ? num.toFixed(1) : num}`];
        }
        if (type === 'int' || type === 'long') {
            return [`${name}: ${defaultValue !== null ? parseInt(defaultValue, 10) : 0}`];
        }
        if (type === 'boolean') {
            return [`${name}: ${defaultValue !== null ? defaultValue === 'true' : false}`];
        }
        return [`${name}: ${yaml.dump(defaultValue ?? '').trim()}`];
    }

    static injectDescription(cwlContent: string, description: string | null): string {
        const doc: any = yaml.load(cwlContent);
        if (description) {
            doc.doc = description;
        } else {
            delete doc.doc;
        }
        return yaml.dump(doc, { lineWidth: -1, noRefs: true });
    }

    static extractDescription(cwlContent: string): string | null {
        try {
            const doc: any = yaml.load(cwlContent);
            return doc?.doc ?? null;
        } catch {
            return null;
        }
    }

    static extractParameters(cwlContent: string): Partial<ParameterDto>[] {
        let doc: any;
        try {
            doc = yaml.load(cwlContent);
        } catch (err: any) {
            throw new Error(`YAML parse error: ${err.message}`);
        }

        const inputs: Record<string, any> = doc?.inputs ?? {};

        return Object.entries(inputs)
            .map(([name, def]) => ({
                name,
                cwlType: String(def?.type ?? 'string').replace(/\?$/, ''),
                defaultValue: def?.default !== undefined ? String(def.default) : null,
                description: def?.doc ?? null,
                direction: ParameterDirection.INPUT,
            }));
    }
}