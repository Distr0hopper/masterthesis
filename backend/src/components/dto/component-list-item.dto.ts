import {ComponentDomain, ComponentSource} from "../enums";
import {ApiProperty} from "@nestjs/swagger";
import {IsDate, IsEnum, IsString} from "class-validator";

export class ComponentListItemDto{
    @ApiProperty()
    id: string;

    @ApiProperty({example: 'RemoveOutliers' })
    @IsString()
    name: string;

    @ApiProperty({example: 'https://github.com/movestore/RemoveOutliers', required: false})
    @IsString()
    repoUrl: string;

    @ApiProperty({ enum: ComponentDomain, required: false})
    @IsEnum(ComponentDomain)
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource})
    @IsEnum(ComponentSource)
    source: ComponentSource;

    @ApiProperty()
    @IsDate()
    createdAt: Date;
}