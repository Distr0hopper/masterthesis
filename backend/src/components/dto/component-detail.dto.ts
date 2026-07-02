import {ApiProperty} from "@nestjs/swagger";
import {ComponentDomain, ComponentSource} from "../enums";
import {Parameter} from "../entities/parameter.entity";

export class ComponentDetailDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    name: string;

    @ApiProperty({ nullable: true })
    repoUrl: string;

    @ApiProperty()
    cwlContent: string;

    @ApiProperty({ enum: ComponentDomain })
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource })
    source: ComponentSource;

    @ApiProperty({ type: () => [Parameter] })
    parameters: Parameter[];

    @ApiProperty()
    createdAt: Date;
}