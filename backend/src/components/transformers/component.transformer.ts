import {Component} from "../entities/component.entity";
import {ComponentListItemDto} from "../dto/component-list-item.dto";
import {ComponentDetailDto} from "../dto/component-detail.dto";

export class ComponentTransformer {
    static toListItem(component: Component): ComponentListItemDto {
        return {
            id: component.id,
            name: component.name,
            repoUrl: component.repoUrl,
            domain: component.domain,
            source: component.source,
            createdAt: component.createdAt,
        };
    }

    static toDetail(component: Component): ComponentDetailDto {
        return {
            id: component.id,
            name: component.name,
            repoUrl: component.repoUrl,
            cwlContent: component.cwlContent,
            domain: component.domain,
            source: component.source,
            parameters: component.parameters,
            createdAt: component.createdAt,
        };
    }
}